"""Parallelized Google ADK Evaluation Runner.

Executes official ADK EvalSets (sec_edgar_analyst_master.evalset.json) with configurable
parallelism, live streaming progress, multi-metric evaluation (Trajectory, ROUGE, and LLM-as-a-Judge),
and formatted summary reporting.
"""

import os
import sys

# Ensure repository root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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

from google.adk.evaluation.rubric_based_final_response_quality_v1 import RubricBasedFinalResponseQualityV1Evaluator
from agent.root_orchestrator import root_agent
from agent.config import settings

from eval.mocks import (
    mock_search_filings_boundary,
    mock_query_metrics_boundary,
    mock_sanitize_user_prompt,
    mock_sanitize_model_response,
    make_mock_credentials,
    parallel_mock_genai_generate_content,
    load_golden_dataset,
    RobustAutoRaterResponseParser,
)

# Patch RubricBasedFinalResponseQualityV1Evaluator to use RobustAutoRaterResponseParser
_orig_rfrq_init = RubricBasedFinalResponseQualityV1Evaluator.__init__

def _robust_rfrq_init(self, eval_metric):
  _orig_rfrq_init(self, eval_metric)
  self._auto_rater_response_parser = RobustAutoRaterResponseParser()

RubricBasedFinalResponseQualityV1Evaluator.__init__ = _robust_rfrq_init

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


def load_eval_set(eval_set_path: str) -> EvalSet:
  """Loads ADK EvalSet from JSON file."""
  with open(eval_set_path, "r", encoding="utf-8") as f:
    data = json.load(f)
  return EvalSet.model_validate(data)


def format_markdown_report(
    eval_set_id: str,
    results: List[EvalCaseResult],
    total_time_sec: float,
    parallelism: int,
    mode: str,
) -> str:
  """Formats a comprehensive markdown summary report of the parallel ADK evaluation run."""
  passed_count = sum(1 for r in results if r.final_eval_status == EvalStatus.PASSED)
  failed_count = len(results) - passed_count
  pass_rate = (passed_count / len(results) * 100.0) if results else 0.0

  # Aggregate metrics pass counts
  metric_stats: Dict[str, Dict[str, Any]] = {}

  for r in results:
    metric_results = getattr(r, "overall_eval_metric_results", None) or getattr(r, "eval_metric_results", None) or []
    for m in metric_results:
      m_name = getattr(m, "metric_name", "unknown")
      m_score = getattr(m, "score", getattr(m, "metric_value", None))
      m_status = getattr(m, "eval_status", None)
      if m_name not in metric_stats:
        metric_stats[m_name] = {"scores": [], "passed": 0, "total": 0}
      metric_stats[m_name]["total"] += 1
      if m_score is not None:
        metric_stats[m_name]["scores"].append(m_score)
      if m_status == EvalStatus.PASSED:
        metric_stats[m_name]["passed"] += 1

  lines = [
      "# 🚀 Parallel ADK Multi-Pillar Evaluation Report",
      f"**Eval Set**: `{eval_set_id}`  ",
      f"**Execution Mode**: `{mode.upper()}`  ",
      f"**Parallelism Workers**: `{parallelism}`  ",
      f"**Total Cases Evaluated**: `{len(results)}`  ",
      f"**Wall-Clock Elapsed Time**: `{total_time_sec:.2f}s` (`{total_time_sec / 60.0:.2f} min`)  ",
      f"**Overall Pass Rate**: `{pass_rate:.1f}%` ({passed_count}/{len(results)})  ",
      "",
      "## Executive Metrics Summary",
      "| Evaluation Pillar / Metric | Description | Evaluator Type | Average Score | Metric Pass Rate | Pillar Status |",
      "| :--- | :--- | :---: | :---: | :---: | :---: |",
  ]

  for m_name, stats in metric_stats.items():
    avg_s = (sum(stats["scores"]) / len(stats["scores"])) if stats["scores"] else 0.0
    p_rate = (stats["passed"] / stats["total"] * 100.0) if stats["total"] else 0.0
    st_icon = "✅ PASS" if stats["passed"] == stats["total"] else "⚠️ REVIEW"

    if "trajectory" in m_name:
      desc = "Tool invocation sequence & argument accuracy"
      e_type = "Deterministic (IN_ORDER)"
      score_fmt = f"`{avg_s:.2f}` / 1.00"
    elif "match_v2" in m_name or "llm" in m_name:
      desc = "LLM Judge Semantic equivalence to golden answer"
      e_type = "LLM-as-a-Judge (Gemini Flash)"
      score_fmt = f"`{avg_s:.2f}` / 1.00"
    elif "rubric" in m_name:
      desc = "Faithfulness, Precision, Completeness & Safety Rubrics"
      e_type = "LLM-as-a-Judge (Rubric V1)"
      score_fmt = f"`{avg_s:.2f}` / 1.00"
    elif "response_match" in m_name:
      desc = "Lexical token / unigram overlap (ROUGE-1 F1)"
      e_type = "Statistical ROUGE-1"
      score_fmt = f"`{avg_s:.4f}`"
    else:
      desc = "General evaluation metric"
      e_type = "Automated Metric"
      score_fmt = f"`{avg_s:.2f}`"

    lines.append(
        f"| **`{m_name}`** | {desc} | {e_type} | {score_fmt} | `{p_rate:.1f}%` ({stats['passed']}/{stats['total']}) | {st_icon} |"
    )

  lines.extend([
      "",
      "## Case-by-Case ADK Trajectory & Response Results",
      "| # | Case ID | Turns | Trajectory Score | ROUGE-1 F1 | LLM Judge Match | LLM Rubrics Quality | Overall Status |",
      "| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
  ])

  for idx, r in enumerate(results, start=1):
    status_icon = "✅ PASSED" if r.final_eval_status == EvalStatus.PASSED else "❌ FAILED"
    inv_count = len(getattr(r, "eval_case_results", []) or []) or 1

    traj_score_str = "—"
    rouge_score_str = "—"
    judge_v2_str = "—"
    rubric_v1_str = "—"

    metric_results = getattr(r, "overall_eval_metric_results", None) or getattr(r, "eval_metric_results", None) or []
    for m in metric_results:
      m_name = getattr(m, "metric_name", "")
      m_val = getattr(m, "score", getattr(m, "metric_value", None))
      if "trajectory" in m_name and m_val is not None:
        traj_score_str = f"`{m_val:.2f}`"
      elif m_name == "response_match_score" and m_val is not None:
        rouge_score_str = f"`{m_val:.4f}`"
      elif "match_v2" in m_name and m_val is not None:
        judge_v2_str = f"`{m_val:.2f}`"
      elif "rubric" in m_name and m_val is not None:
        rubric_v1_str = f"`{m_val:.2f}`"

    lines.append(
        f"| {idx} | `{r.eval_id}` | {inv_count} | {traj_score_str} | {rouge_score_str} | {judge_v2_str} | {rubric_v1_str} | {status_icon} |"
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
  print(f"🚀 PARALLEL ADK EVALUATION RUNNER (TRAJECTORY, ROUGE & LLM-AS-A-JUDGE)")
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

  print(f"Active Evaluation Metrics ({len(eval_metrics)}):")
  for em in eval_metrics:
    print(f"  • {em.metric_name} (Threshold: {getattr(em.criterion, 'threshold', 'N/A')})")

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
  live_timeout = eval_config.live_model_config.timeout_seconds if eval_config.live_model_config else 180
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

  print(f"\n[Phase 2/2] Running Parallel Multi-Pillar Metric Evaluation (Trajectory, ROUGE, LLM Judge)...")
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
  parser = argparse.ArgumentParser(description="Parallelized Google ADK Evaluation Runner with LLM-as-a-Judge")
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
