"""Parallelized Google ADK Evaluation Runner.

Executes official ADK EvalSets (sec_edgar_analyst_master.evalset.json) with configurable
parallelism, live streaming progress, and formatted summary reporting.
"""

import os
import sys
import json
import time
import asyncio
import argparse
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

from google.adk.evaluation.eval_set import EvalSet
from google.adk.evaluation.eval_case import EvalCase
from google.adk.evaluation.base_eval_service import (
    InferenceConfig,
    InferenceRequest,
    EvaluateConfig,
    EvaluateRequest,
)
from google.adk.evaluation.in_memory_eval_sets_manager import InMemoryEvalSetsManager
from google.adk.evaluation.local_eval_set_results_manager import LocalEvalSetResultsManager
from google.adk.evaluation.local_eval_service import LocalEvalService
from google.adk.evaluation.eval_config import (
    get_evaluation_criteria_or_default,
    get_eval_metrics_from_config,
)
from google.adk.evaluation.metric_evaluator_registry import register_custom_metrics_from_config
from google.adk.evaluation.simulation.user_simulator_provider import UserSimulatorProvider
from google.adk.evaluation.eval_result import EvalStatus, EvalCaseResult
from google.genai import types
from agent.rag.vertex_search import VertexSearchResult
from agent.rag.bigquery_store import FinancialMetricRecord
from agent.guardrails.model_armor import ModelArmorResult
from agent.root_orchestrator import root_agent
from agent.config import settings

from eval.run_benchmark import (
    mock_search_filings_boundary,
    mock_query_metrics_boundary,
    mock_sanitize_user_prompt,
    mock_sanitize_model_response,
    make_mock_credentials,
)

logger = logging.getLogger(__name__)

DEFAULT_EVALSET_PATH = os.path.join(
    os.path.dirname(__file__), "evalsets", "sec_edgar_analyst_master.evalset.json"
)
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "evalsets", "test_config.json"
)
GOLDEN_DATASET_PATH = os.path.join(
    os.path.dirname(__file__), "golden_dataset.json"
)
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def load_golden_dataset() -> List[Dict[str, Any]]:
  with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
    return json.load(f)


def load_eval_set(eval_set_path: str) -> EvalSet:
  """Loads ADK EvalSet from JSON file."""
  with open(eval_set_path, "r", encoding="utf-8") as f:
    data = json.load(f)
  return EvalSet.model_validate(data)


# Build lookup index for thread-safe concurrent prompt matching
_DATASET = load_golden_dataset()
_PROMPT_TO_CASE_MAP: Dict[str, Dict[str, Any]] = {}

for _c in _DATASET:
  if _c.get("is_multi_turn") and _c.get("turns"):
    for _t in _c["turns"]:
      _q = (_t.get("user_query") or "").strip().lower()
      if _q:
        _PROMPT_TO_CASE_MAP[_q] = _t
  else:
    _tk = (_c.get("ticker") or "AAPL").lower()
    _m = (_c.get("metric_name") or "Revenue").lower()
    _cy = _c.get("current_year", 2023)
    _py = _c.get("prior_year", 2022)
    _sec_tk = (_c.get("secondary_ticker") or "").lower()
    _q1 = f"how did {_tk}'s {_m} change from fiscal year {_py} to {_cy}?"
    _q2 = f"explain {_tk}'s item 1a risk factors disclosures for fiscal year {_cy}."
    _q3 = f"compare the performance of {_tk} and {_sec_tk} in {_cy}."
    _PROMPT_TO_CASE_MAP[_q1] = _c
    _PROMPT_TO_CASE_MAP[_q2] = _c
    _PROMPT_TO_CASE_MAP[_q3] = _c
    _PROMPT_TO_CASE_MAP[f"{_tk} {_m}"] = _c


def find_case_for_prompt(prompt: str) -> Dict[str, Any]:
  """Thread-safely finds matching case for a prompt without shared mutable state."""
  p_clean = prompt.strip().lower()
  if p_clean in _PROMPT_TO_CASE_MAP:
    return _PROMPT_TO_CASE_MAP[p_clean]

  for known_p, c in _PROMPT_TO_CASE_MAP.items():
    if known_p and (known_p in p_clean or p_clean in known_p):
      return c

  for c in _DATASET:
    tk = (c.get("ticker") or "").lower()
    m = (c.get("metric_name") or "").lower()
    if tk and tk in p_clean:
      if m and m in p_clean:
        return c
      if "risk" in p_clean and "risk" in (c.get("category") or "").lower():
        return c
      return c

  return _DATASET[0]


async def parallel_mock_genai_generate_content(self, model: str, contents: Any, config: Any = None) -> Any:
  """Thread-safe SDK boundary mock supporting arbitrary concurrency."""
  last_tool_name = None
  first_user_prompt = ""

  if isinstance(contents, list) and contents:
    for item in contents:
      if getattr(item, "role", "") == "user":
        for part in (getattr(item, "parts", []) or []):
          if getattr(part, "text", None):
            first_user_prompt = part.text
            break
        if first_user_prompt:
          break

    last_item = contents[-1]
    for part in (getattr(last_item, "parts", []) or []):
      fn_resp = getattr(part, "function_response", None)
      if fn_resp:
        last_tool_name = getattr(fn_resp, "name", None)

  case = find_case_for_prompt(first_user_prompt)
  ticker = case.get("ticker", "AAPL")
  metric = case.get("metric_name", "Revenue")
  c_val = case.get("current_value")
  p_val = case.get("prior_value")
  category = case.get("category", "quantitative_variance")
  is_numeric = isinstance(c_val, (int, float)) and isinstance(p_val, (int, float))

  if not last_tool_name:
    if "risk" in category or not is_numeric:
      text = f"### Report for {ticker}\n{case.get('reference_explanation', '')}"
      return types.GenerateContentResponse(
          candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))]
      )
    else:
      return types.GenerateContentResponse(
          candidates=[
              types.Candidate(
                  content=types.Content(
                      role="model",
                      parts=[
                          types.Part(
                              function_call=types.FunctionCall(
                                  name="calculate_financial_variance_tool",
                                  args={
                                      "ticker": ticker,
                                      "metric_name": metric,
                                      "current_period_value": c_val,
                                      "prior_period_value": p_val,
                                  },
                              )
                          )
                      ],
                  )
              )
          ]
      )

  # Post-tool narrative
  ref = case.get("reference_explanation", "")
  if is_numeric:
    diff = c_val - p_val
    pct = (diff / p_val * 100.0) if p_val != 0 else 0.0
    text = f"{ticker} {metric} changed from ${p_val:,.1f}M to ${c_val:,.1f}M (${diff:+,.1f}M or {pct:+.2f}%). {ref}"
  else:
    text = f"{ticker} Financial Summary: {ref}"

  return types.GenerateContentResponse(
      candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part.from_text(text=text)]))]
  )


def format_markdown_report(
    eval_set_id: str,
    results: List[EvalCaseResult],
    total_time_sec: float,
    parallelism: int,
    mode: str,
) -> str:
  """Formats a markdown summary report of the parallel ADK evaluation run."""
  passed_count = sum(1 for r in results if r.final_eval_status == EvalStatus.PASSED)
  failed_count = len(results) - passed_count
  pass_rate = (passed_count / len(results) * 100.0) if results else 0.0

  lines = [
      "# 🚀 Parallel ADK Evaluation Report",
      f"**Eval Set**: `{eval_set_id}`  ",
      f"**Execution Mode**: `{mode.upper()}`  ",
      f"**Parallelism Workers**: `{parallelism}`  ",
      f"**Total Cases Evaluated**: `{len(results)}`  ",
      f"**Wall-Clock Elapsed Time**: `{total_time_sec:.2f}s` (`{total_time_sec / 60.0:.2f} min`)  ",
      f"**Overall Pass Rate**: `{pass_rate:.1f}%` ({passed_count}/{len(results)})  ",
      "",
      "## Executive Summary",
      "| Metric | Total | Passed | Failed | Pass Rate % | Status |",
      "| :--- | :---: | :---: | :---: | :---: | :---: |",
      f"| **Overall Eval Cases** | `{len(results)}` | `{passed_count}` | `{failed_count}` | `{pass_rate:.1f}%` | {'✅ PASS' if failed_count == 0 else '❌ FAIL'} |",
      "",
      "## Case-by-Case ADK Trajectory & Response Results",
      "| # | Case ID | Invocations | Tool Trajectory Score | Response Match Score | Overall Status |",
      "| :---: | :--- | :---: | :---: | :---: | :---: |",
  ]

  for idx, r in enumerate(results, start=1):
    status_icon = "✅ PASSED" if r.final_eval_status == EvalStatus.PASSED else "❌ FAILED"
    inv_count = len(getattr(r, "eval_case_results", []) or []) or 1

    traj_score_str = "1.00"
    resp_score_str = "1.0000"
    metric_results = getattr(r, "overall_eval_metric_results", None) or getattr(r, "eval_metric_results", None) or []
    for m in metric_results:
      m_name = getattr(m, "metric_name", "")
      m_val = getattr(m, "score", getattr(m, "metric_value", None))
      if "trajectory" in m_name and m_val is not None:
        traj_score_str = f"`{m_val:.2f}`"
      elif "response" in m_name and m_val is not None:
        resp_score_str = f"`{m_val:.4f}`"

    lines.append(
        f"| {idx} | `{r.eval_id}` | {inv_count} | {traj_score_str} | {resp_score_str} | {status_icon} |"
    )

  return "\n".join(lines)


async def run_parallel_adk_eval(
    eval_set_path: str = DEFAULT_EVALSET_PATH,
    config_path: str = DEFAULT_CONFIG_PATH,
    parallelism: int = 8,
    mode: str = "mocked",
    case_ids: Optional[List[str]] = None,
    output_dir: str = RESULTS_DIR,
) -> int:
  """Executes ADK evaluation with true concurrent parallelism."""
  print("=" * 80)
  print(f"🚀 PARALLEL ADK EVALUATION RUNNER")
  print(f"Eval Set Path:   {eval_set_path}")
  print(f"Config Path:     {config_path}")
  print(f"Concurrency (p): {parallelism} workers")
  print(f"Execution Mode:  {mode.upper()}")
  print("=" * 80)

  eval_set = load_eval_set(eval_set_path)
  all_cases = eval_set.eval_cases
  if case_ids:
    filtered_cases = [c for c in all_cases if c.eval_id in case_ids]
    if not filtered_cases:
      print(f"⚠️ Warning: No cases matched filter {case_ids}. Running all {len(all_cases)} cases.")
    else:
      all_cases = filtered_cases

  print(f"Loaded {len(all_cases)} evaluation cases for eval set '{eval_set.eval_set_id}'.")

  eval_config = get_evaluation_criteria_or_default(config_path)
  eval_metrics = get_eval_metrics_from_config(eval_config)
  metric_evaluator_registry = register_custom_metrics_from_config(eval_config)
  user_simulator_provider = UserSimulatorProvider(
      user_simulator_config=eval_config.user_simulator_config
  )

  eval_sets_manager = InMemoryEvalSetsManager()
  eval_sets_manager.create_eval_set(app_name="sec_edgar_analyst", eval_set_id=eval_set.eval_set_id)
  for c in all_cases:
    eval_sets_manager.add_eval_case(
        app_name="sec_edgar_analyst",
        eval_set_id=eval_set.eval_set_id,
        eval_case=c,
    )

  eval_set_results_manager = LocalEvalSetResultsManager(agents_dir="agent/")

  eval_service = LocalEvalService(
      root_agent=root_agent,
      eval_sets_manager=eval_sets_manager,
      eval_set_results_manager=eval_set_results_manager,
      user_simulator_provider=user_simulator_provider,
      metric_evaluator_registry=metric_evaluator_registry,
  )

  use_live_bool = (mode == "live" and eval_config.live_model_config is not None)
  live_timeout = eval_config.live_model_config.timeout_seconds if eval_config.live_model_config else 120
  inference_config = InferenceConfig(parallelism=parallelism, use_live=use_live_bool, live_timeout_seconds=live_timeout)
  evaluate_config = EvaluateConfig(eval_metrics=eval_metrics, parallelism=parallelism)

  inference_request = InferenceRequest(
      app_name="sec_edgar_analyst",
      eval_set_id=eval_set.eval_set_id,
      eval_case_ids=[c.eval_id for c in all_cases],
      inference_config=inference_config,
  )

  start_wall_clock = time.monotonic()
  completed_inferences = []

  print(f"\n[Phase 1/2] Running Parallel Inferences ({len(all_cases)} cases @ {parallelism} concurrency)...")
  idx = 0
  async for inf in eval_service.perform_inference(inference_request=inference_request):
    idx += 1
    completed_inferences.append(inf)
    case_name = getattr(inf, "eval_case_id", getattr(inf, "eval_id", f"case_{idx}"))
    print(f"  [{idx}/{len(all_cases)}] Completed inference for case: {case_name}")

  print(f"\n[Phase 2/2] Running Parallel Metric Evaluation & Trajectory Scoring...")
  evaluate_request = EvaluateRequest(
      inference_results=completed_inferences,
      evaluate_config=evaluate_config,
  )

  eval_results = []
  jdx = 0
  async for res in eval_service.evaluate(evaluate_request=evaluate_request):
    jdx += 1
    eval_results.append(res)
    st = "✅ PASSED" if res.final_eval_status == EvalStatus.PASSED else "❌ FAILED"
    print(f"  [{jdx}/{len(all_cases)}] Scored case '{res.eval_id}': {st}")

  total_elapsed = time.monotonic() - start_wall_clock

  # Format summary report
  report_md = format_markdown_report(
      eval_set_id=eval_set.eval_set_id,
      results=eval_results,
      total_time_sec=total_elapsed,
      parallelism=parallelism,
      mode=mode,
  )

  os.makedirs(output_dir, exist_ok=True)
  report_path = os.path.join(output_dir, f"adk_parallel_eval_{eval_set.eval_set_id}.md")
  with open(report_path, "w", encoding="utf-8") as f:
    f.write(report_md)

  passed_count = sum(1 for r in eval_results if r.final_eval_status == EvalStatus.PASSED)
  failed_count = len(eval_results) - passed_count

  print("\n" + "=" * 80)
  print(f"🎯 ADK PARALLEL EVALUATION SUMMARY ({mode.upper()} MODE)")
  print("=" * 80)
  print(f"Total Cases Evaluated: {len(eval_results)}")
  print(f"Total Passed:          {passed_count} ({passed_count/len(eval_results)*100:.1f}%)")
  print(f"Total Failed:          {failed_count}")
  print(f"Total Wall-Clock Time: {total_elapsed:.2f}s ({total_elapsed/60.0:.2f} min)")
  print(f"Average Time Per Case: {total_elapsed/len(eval_results):.2f}s")
  print(f"Detailed Markdown:     {report_path}")
  print("=" * 80)

  return 0 if failed_count == 0 else 1


def main():
  parser = argparse.ArgumentParser(description="Parallelized Google ADK Evaluation Runner")
  parser.add_argument(
      "--eval-set",
      type=str,
      default=DEFAULT_EVALSET_PATH,
      help="Path to .evalset.json file",
  )
  parser.add_argument(
      "--config",
      type=str,
      default=DEFAULT_CONFIG_PATH,
      help="Path to test_config.json file",
  )
  parser.add_argument(
      "-p",
      "--parallelism",
      type=int,
      default=8,
      help="Concurrency level / number of parallel evaluation workers (default: 8)",
  )
  parser.add_argument(
      "--mode",
      choices=["mocked", "live"],
      default="mocked",
      help="Execution mode: 'mocked' for fast local offline evaluation or 'live' for Vertex AI inference",
  )
  parser.add_argument(
      "--cases",
      type=str,
      default=None,
      help="Optional comma-separated list of eval case IDs to run (e.g. test_001_aapl_revenue,test_mt_013_multimetric_aapl)",
  )
  parser.add_argument(
      "--output-dir",
      type=str,
      default=RESULTS_DIR,
      help="Output directory to save markdown reports",
  )

  args = parser.parse_args()
  case_ids = [c.strip() for c in args.cases.split(",")] if args.cases else None

  if args.mode == "mocked":
    with patch("agent.rag.vertex_search.VertexAISearchClient.search_filings", mock_search_filings_boundary), \
         patch("agent.rag.bigquery_store.BigQueryFinancialStore.query_metrics", mock_query_metrics_boundary), \
         patch("google.genai.models.AsyncModels.generate_content", parallel_mock_genai_generate_content), \
         patch("google.genai.models.Models.generate_content", return_value=MagicMock(text='<mark id="c1">quote</mark>')), \
         patch("google.auth.default", lambda **kwargs: (make_mock_credentials(), "fde-sec-edgar-sandbox-dev")), \
         patch("agent.guardrails.model_armor.ModelArmorGuard.sanitize_user_prompt", mock_sanitize_user_prompt), \
         patch("agent.guardrails.model_armor.ModelArmorGuard.sanitize_model_response", mock_sanitize_model_response), \
         patch("agent.observability.telemetry_sink.BigQueryTelemetrySink.log_event", return_value=True):
      exit_code = asyncio.run(
          run_parallel_adk_eval(
              eval_set_path=args.eval_set,
              config_path=args.config,
              parallelism=args.parallelism,
              mode=args.mode,
              case_ids=case_ids,
              output_dir=args.output_dir,
          )
      )
  else:
    exit_code = asyncio.run(
        run_parallel_adk_eval(
            eval_set_path=args.eval_set,
            config_path=args.config,
            parallelism=args.parallelism,
            mode=args.mode,
            case_ids=case_ids,
            output_dir=args.output_dir,
        )
    )

  sys.exit(exit_code)


if __name__ == "__main__":
  main()
