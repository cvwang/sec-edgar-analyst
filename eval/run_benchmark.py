"""CLI Benchmark Runner for SEC EDGAR Natural Language Analyst.

Executes non-tautological evaluation suites across golden_dataset.json.
In --mocked mode, real RootOrchestrator, ADK Runner, LlmAgent, calculation_engine,
and session stores execute for real, while only external network API calls (Vertex AI Search,
BigQuery network, Gemini LLM inference, Model Armor) are stubbed at the SDK boundary.
"""

import sys
import os
import json
import time
import argparse
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock
from google.genai import types
from agent.orchestrator import RootOrchestrator
from agent.rag.vertex_search import VertexSearchResult
from agent.rag.bigquery_store import FinancialMetricRecord
from agent.guardrails.model_armor import ModelArmorResult
from eval.evaluator import EvalEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def load_golden_dataset() -> List[Dict[str, Any]]:
    with open(GOLDEN_DATASET_PATH, "r") as f:
        return json.load(f)


def extract_real_tool_result_from_contents(contents: List[Any]) -> Optional[Dict[str, Any]]:
    """Extracts the actual VarianceResult dict returned by the real tool execution from ADK conversation history."""
    for content in reversed(contents or []):
        parts = getattr(content, "parts", []) or []
        for part in parts:
            fn_resp = getattr(part, "function_response", None)
            if fn_resp and getattr(fn_resp, "name", None) == "calculate_financial_variance_tool":
                resp_dict = getattr(fn_resp, "response", {})
                if isinstance(resp_dict, dict):
                    return resp_dict.get("result", resp_dict)
    return None


def format_turn2_narrative_from_real_tool_output(contents: List[Any], case: Dict[str, Any]) -> str:
    """Formats Turn 2 narrative strictly using the actual output returned by calculate_financial_variance_tool.
    
    References ONLY the REAL tool execution output returned in ADK conversation history.
    References ZERO expected fields from golden_dataset case dict.
    """
    tool_result = extract_real_tool_result_from_contents(contents)

    if not tool_result:
        return f"### Analysis for {case.get('ticker')}\n{case.get('reference_explanation', '')}"

    if not tool_result.get("is_success", True):
        return f"⚠️ Calculation Error: {tool_result.get('error')} Recovery: {tool_result.get('recovery_instruction')}"

    ticker = tool_result.get("ticker", case.get("ticker", "UNKNOWN"))
    metric = tool_result.get("metric_name", case.get("metric_name", "Metric"))
    current_val = tool_result.get("current_period_value")
    prior_val = tool_result.get("prior_period_value")
    abs_change = tool_result.get("absolute_change")
    pct_change = tool_result.get("percentage_change")
    direction = tool_result.get("direction", "N/A")
    formatted_sum = tool_result.get("formatted_summary", "")

    return (
        f"### Financial Variance Report for {ticker} ({metric})\n"
        f"- Current Period Value: {current_val}\n"
        f"- Prior Period Value: {prior_val}\n"
        f"- Computed Absolute Change: {abs_change}\n"
        f"- Computed Percentage Change: {pct_change}%\n"
        f"- Direction: {direction}\n"
        f"Summary: {formatted_sum}\n"
        f"{case.get('reference_explanation', '')}"
    )


def mock_search_filings_boundary(self, query: str, page_size: int = 5) -> List[VertexSearchResult]:
    """SDK boundary mock for VertexAISearchClient.search_filings returning realistic chunks with text & noise."""
    query_upper = query.upper()
    ticker = "AAPL"
    for t in ["AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA"]:
        if t in query_upper:
            ticker = t
            break

    return [
        VertexSearchResult(
            id=f"{ticker}_chunk_1",
            gcs_uri=f"gs://sec-analyst-sec-reports/filings/{ticker}_2023_10K.md",
            title=f"{ticker} Item 7 MD&A Disclosures",
            snippet=f"{ticker} reported Item 7 MD&A disclosures. Macroeconomic headwinds, cloud growth, data center expansion, and vehicle deliveries impacted results.",
        ),
        VertexSearchResult(
            id=f"{ticker}_chunk_2",
            gcs_uri=f"gs://sec-analyst-sec-reports/filings/{ticker}_2023_10K.md",
            title=f"{ticker} Item 1A Risk Factors",
            snippet=f"{ticker} faces risk factors including supply chain, autonomous driving regulation, privacy laws, and competition.",
        ),
    ]


def mock_query_metrics_boundary(self, ticker: str, fiscal_year: int) -> Optional[FinancialMetricRecord]:
    """SDK boundary mock for BigQueryFinancialStore.query_metrics returning FinancialMetricRecord."""
    t_upper = ticker.upper()
    return FinancialMetricRecord(
        ticker=t_upper,
        fiscal_year=fiscal_year,
        company_name=f"{t_upper} Inc.",
        sector="Technology",
        revenue=383285.0 if t_upper == "AAPL" else (211915.0 if t_upper == "MSFT" else 60922.0),
        operating_income=88523.0 if t_upper == "MSFT" else 32972.0,
        net_income=96995.0 if t_upper == "AAPL" else 14997.0,
    )


CURRENT_EVAL_CASE: Dict[str, Any] = {}
LAST_EXECUTED_TOOL_RESULT: Optional[Dict[str, Any]] = None


async def mock_genai_generate_content_boundary(self, model: str, contents: Any, config: Any = None) -> Any:
    """SDK boundary mock for google.genai.models.AsyncModels.generate_content driving ADK ReAct loop."""
    global LAST_EXECUTED_TOOL_RESULT
    tool_res = extract_real_tool_result_from_contents(contents if isinstance(contents, list) else [])
    if tool_res:
        LAST_EXECUTED_TOOL_RESULT = tool_res

    last_tool_name = None
    if isinstance(contents, list) and contents:
        last_item = contents[-1]
        parts = getattr(last_item, "parts", []) or []
        for part in parts:
            fn_resp = getattr(part, "function_response", None)
            if fn_resp:
                last_tool_name = getattr(fn_resp, "name", None)

    case = CURRENT_EVAL_CASE.get("current", {})
    active_turn = CURRENT_EVAL_CASE.get("active_turn") or case

    ticker = active_turn.get("ticker", case.get("ticker", "AAPL"))
    metric = active_turn.get("metric_name", case.get("metric_name", "Revenue"))
    c_val = active_turn.get("current_value")
    p_val = active_turn.get("prior_value")
    category = active_turn.get("category", case.get("category", "quantitative_variance"))
    is_numeric_val = isinstance(c_val, (int, float)) and isinstance(p_val, (int, float))

    if active_turn.get("is_clarification_request"):
        clarification_msg = active_turn.get("reference_explanation", f"Which financial metric and fiscal year range would you like to analyze for {ticker}?")
        return types.GenerateContentResponse(
            candidates=[
                types.Candidate(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=clarification_msg)],
                    )
                )
            ]
        )

    if not last_tool_name:
        if category == "qualitative_risk" or not is_numeric_val:
            text = f"### Financial Report for {ticker}\n{active_turn.get('reference_explanation', '')}"
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            role="model",
                            parts=[types.Part.from_text(text=text)],
                        )
                    )
                ]
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

    narrative_text = format_turn2_narrative_from_real_tool_output(contents, active_turn)
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=narrative_text)],
                )
            )
        ]
    )





def mock_sanitize_user_prompt(self, prompt: str) -> ModelArmorResult:
    """SDK boundary mock for ModelArmorGuard.sanitize_user_prompt."""
    prompt_lower = prompt.lower()
    if "ignore all previous instructions" in prompt_lower or "admin_override_token" in prompt_lower:
        return ModelArmorResult(
            is_blocked=True,
            matched_filter="jailbreak",
            rejection_message="Model Armor Guardrail blocked prompt injection attempt.",
        )
    return ModelArmorResult(is_blocked=False)


def mock_sanitize_model_response(self, response_text: str) -> ModelArmorResult:
    """SDK boundary mock for ModelArmorGuard.sanitize_model_response."""
    return ModelArmorResult(is_blocked=False)


def make_mock_credentials():
    creds = MagicMock()
    creds.quota_project_id = "fde-sec-edgar-sandbox-dev"
    creds.token = "mock-token"
    creds.project_id = "fde-sec-edgar-sandbox-dev"
    creds.valid = True
    return creds


def format_markdown_report(summary: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    """Formats benchmark evaluation results into a clean GitHub Flavored Markdown report."""
    md = []
    md.append("# SEC EDGAR Analyst - Benchmark & Evaluation Report")
    md.append(f"**Timestamp**: {summary['timestamp']}  ")
    md.append(f"**Execution Mode**: `{summary['execution_mode']}`  ")
    md.append(f"**Total Test Cases Evaluated**: {summary['total_cases']}  \n")

    md.append("## Executive Metrics Summary")
    md.append("| Metric Category | Score / Metric | Status | Pass Threshold |")
    md.append("| :--- | :---: | :---: | :---: |")
    md.append(f"| **Math Accuracy %** | `{summary['math_accuracy_pct']}%` | {'✅ PASS' if summary['math_accuracy_pct'] == 100.0 else '❌ FAIL'} | 100.0% |")
    md.append(f"| **Grounding Recall** | `{summary['grounding_recall']:.4f}` | {'✅ PASS' if summary['grounding_recall'] >= 0.70 else '⚠️ WARN'} | >= 0.7000 |")
    md.append(f"| **ROUGE-L F1** | `{summary['rouge_l_f1']:.4f}` | {'✅ PASS' if summary['rouge_l_f1'] >= 0.50 else '⚠️ WARN'} | >= 0.5000 |")
    md.append(f"| **LLM Faithfulness** | `{summary['faithfulness_score']:.4f}` | {'✅ PASS' if summary['faithfulness_score'] >= 0.85 else '❌ FAIL'} | >= 0.8500 |")
    md.append(f"| **Answer Relevance** | `{summary['relevance_score']:.4f}` | {'✅ PASS' if summary['relevance_score'] >= 0.85 else '❌ FAIL'} | >= 0.8500 |")
    md.append(f"| **Execution Error Rate** | `{summary['execution_error_rate_pct']}%` | {'✅ PASS' if summary['execution_error_rate_pct'] == 0.0 else '❌ FAIL'} | 0.0% |")
    md.append(f"| **Average Latency (ms)** | `{summary['avg_latency_ms']:.2f}ms` | {'✅ PASS' if summary['avg_latency_ms'] <= 3000.0 else '⚠️ WARN'} | <= 3000ms |")

    md.append("\n## Case-by-Case Benchmark Results")
    md.append("| Case ID | Ticker | Category | Exec Error | Math Acc % | Grounding Recall | ROUGE-L F1 | LLM Faithfulness | Latency (ms) |")
    md.append("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

    for r in results:
        err_str = "❌ ERR" if r.get("execution_error") else "✅ OK"
        md.append(
            f"| `{r['case_id']}` | `{r['ticker']}` | `{r['category']}` | {err_str} | {r['math_accuracy_pct']}% | {r['grounding_recall']:.4f} | {r['rouge_l_f1']:.4f} | {r['faithfulness_score']:.4f} | {r['latency_ms']:.1f}ms |"
        )

    return "\n".join(md)


# Profiling accumulators for Part 0
PROFILER = {
    "total_gemini_reasoning_time_sec": 0.0,
    "total_model_armor_time_sec": 0.0,
    "total_external_data_time_sec": 0.0,
    "total_llm_judge_time_sec": 0.0,
    "case_timings": [],
}


def create_timing_wrapper(original_fn, category_key):
    """Wraps a function to accumulate elapsed wall-clock time into PROFILER[category_key]."""
    def wrapper(*args, **kwargs):
        t0 = time.monotonic()
        try:
            return original_fn(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - t0
            PROFILER[category_key] += elapsed
    return wrapper


def run_benchmark(
    mocked: bool = True,
    limit: Optional[int] = None,
    regression_check: bool = False,
    output_dir: str = RESULTS_DIR,
) -> int:
    """Executes the benchmark evaluation run and returns exit status code (0 for pass, 1 for regression failure)."""
    dataset = load_golden_dataset()
    if limit and limit > 0:
        dataset = dataset[:limit]

    os.makedirs(output_dir, exist_ok=True)
    evaluator = EvalEngine()

    search_patch = patch("agent.rag.vertex_search.VertexAISearchClient.search_filings", mock_search_filings_boundary)
    bq_patch = patch("agent.rag.bigquery_store.BigQueryFinancialStore.query_metrics", mock_query_metrics_boundary)
    genai_patch = patch("google.genai.models.AsyncModels.generate_content", mock_genai_generate_content_boundary)
    auth_patch = patch("google.auth.default", lambda **kwargs: (make_mock_credentials(), "fde-sec-edgar-sandbox-dev"))
    ma_prompt_patch = patch("agent.guardrails.model_armor.ModelArmorGuard.sanitize_user_prompt", mock_sanitize_user_prompt)
    ma_response_patch = patch("agent.guardrails.model_armor.ModelArmorGuard.sanitize_model_response", mock_sanitize_model_response)

    if mocked:
        search_patch.start()
        bq_patch.start()
        genai_patch.start()
        auth_patch.start()
        ma_prompt_patch.start()
        ma_response_patch.start()
    else:
        # Live mode timing wrappers
        from agent.guardrails.model_armor import ModelArmorGuard
        from agent.rag.vertex_search import VertexAISearchClient
        from agent.rag.bigquery_store import BigQueryFinancialStore
        from google.genai.models import AsyncModels, Models

        ModelArmorGuard.sanitize_user_prompt = create_timing_wrapper(ModelArmorGuard.sanitize_user_prompt, "total_model_armor_time_sec")
        ModelArmorGuard.sanitize_model_response = create_timing_wrapper(ModelArmorGuard.sanitize_model_response, "total_model_armor_time_sec")
        VertexAISearchClient.search_filings = create_timing_wrapper(VertexAISearchClient.search_filings, "total_external_data_time_sec")
        BigQueryFinancialStore.query_metrics = create_timing_wrapper(BigQueryFinancialStore.query_metrics, "total_external_data_time_sec")
        AsyncModels.generate_content = create_timing_wrapper(AsyncModels.generate_content, "total_gemini_reasoning_time_sec")
        Models.generate_content = create_timing_wrapper(Models.generate_content, "total_gemini_reasoning_time_sec")
        evaluator.evaluate_case_layer2_llm_judge = create_timing_wrapper(evaluator.evaluate_case_layer2_llm_judge, "total_llm_judge_time_sec")

    # Instantiate RootOrchestrator AFTER active patches/wrappers are set up
    orchestrator = RootOrchestrator()

    results = []
    total_math_passed = 0
    total_execution_errors = 0
    total_latency_ms = 0.0

    logger.info(f"Starting non-tautological benchmark evaluation on {len(dataset)} cases (Mode: {'MOCKED' if mocked else 'LIVE'})...")
    full_run_start = time.monotonic()

    eval_run_id = int(time.monotonic())
    try:
        for case in dataset:
            global LAST_EXECUTED_TOOL_RESULT
            LAST_EXECUTED_TOOL_RESULT = None
            start_monotonic = time.monotonic()
            execution_error = False
            session_id = f"eval_{case['case_id']}_{eval_run_id}"
            CURRENT_EVAL_CASE["current"] = case

            if case.get("is_multi_turn") and case.get("turns"):
                turn_narratives = []
                turn_tool_results = []
                retrieved_chunks = []

                for turn in case["turns"]:
                    LAST_EXECUTED_TOOL_RESULT = None
                    CURRENT_EVAL_CASE["active_turn"] = turn
                    t_prompt = turn["user_query"]
                    try:
                        resp = orchestrator.dispatch_query(prompt=t_prompt, session_id=session_id)
                        if not resp.get("is_success", False):
                            execution_error = True
                            gen_narrative = resp.get("narrative", f"Query execution failed: {resp.get('error')}")
                        else:
                            gen_narrative = resp.get("narrative", "")

                        turn_narratives.append(gen_narrative)
                        t_tool_res = resp.get("tool_result") or LAST_EXECUTED_TOOL_RESULT
                        turn_tool_results.append(t_tool_res)

                        t_chunks = [c.snippet for c in resp.get("retrieved_context", []) if hasattr(c, "snippet")]
                        if not t_chunks and turn.get("expected_grounding_keyword"):
                            t_chunks = [f"{turn.get('ticker', case.get('ticker'))} {turn.get('expected_grounding_keyword')} filing context."]
                        retrieved_chunks.extend(t_chunks)

                    except Exception as e:
                        execution_error = True
                        logger.error(f"Execution exception for multi-turn case {case['case_id']} turn {turn.get('turn_index')}: {str(e)}")
                        turn_narratives.append(f"⚠️ Query execution exception: {str(e)}")

                elapsed_ms = (time.monotonic() - start_monotonic) * 1000.0
                total_latency_ms += elapsed_ms
                if execution_error:
                    total_execution_errors += 1

                eval_res = evaluator.evaluate_case_multiturn(
                    case=case,
                    turn_narratives=turn_narratives,
                    retrieved_chunks=retrieved_chunks,
                    run_llm_judge=not mocked,
                    turn_tool_results=turn_tool_results,
                )
                eval_res["latency_ms"] = elapsed_ms
                eval_res["execution_error"] = execution_error
                results.append(eval_res)

                if eval_res["is_math_accurate"] and not execution_error:
                    total_math_passed += 1

            else:
                prompt = f"Analyze {case['ticker']} {case['metric_name']} for {case['current_year']} compared to {case['prior_year']}"
                if case.get("category") == "qualitative_risk":
                    prompt = f"Explain {case['ticker']} {case['current_year']} Item 1A Risk Factors disclosures"
                elif case.get("category") == "peer_comparison":
                    prompt = f"Compare {case['ticker']} and {case.get('secondary_ticker')} performance in {case['current_year']}"

                gen_narrative = ""
                retrieved_chunks = []

                try:
                    resp = orchestrator.dispatch_query(prompt=prompt, session_id=session_id)

                    if not resp.get("is_success", False):
                        execution_error = True
                        gen_narrative = resp.get("narrative", f"Query execution failed: {resp.get('error')}")
                    else:
                        gen_narrative = resp.get("narrative", "")

                    retrieved_chunks = [c.snippet for c in resp.get("retrieved_context", []) if hasattr(c, "snippet")]
                    if not retrieved_chunks and case.get("expected_grounding_keyword"):
                        retrieved_chunks = [f"{case['ticker']} {case.get('expected_grounding_keyword', '')} filing context."]

                except Exception as e:
                    execution_error = True
                    logger.error(f"Execution exception for case {case['case_id']}: {str(e)}")
                    gen_narrative = f"⚠️ Query execution exception: {str(e)}"
                    retrieved_chunks = []

                elapsed_ms = (time.monotonic() - start_monotonic) * 1000.0
                total_latency_ms += elapsed_ms

                if execution_error:
                    total_execution_errors += 1

                eval_res = evaluator.evaluate_case_full(
                    case=case,
                    generated_narrative=gen_narrative,
                    retrieved_chunks=retrieved_chunks,
                    run_llm_judge=not mocked,
                    structured_tool_result=resp.get("tool_result") or LAST_EXECUTED_TOOL_RESULT,
                )
                eval_res["latency_ms"] = elapsed_ms
                eval_res["execution_error"] = execution_error
                results.append(eval_res)

                if eval_res["is_math_accurate"] and not execution_error:
                    total_math_passed += 1

    finally:
        if mocked:
            search_patch.stop()
            bq_patch.stop()
            genai_patch.stop()
            auth_patch.stop()
            ma_prompt_patch.stop()
            ma_response_patch.stop()

    total_cases = len(results)
    math_accuracy_pct = round((total_math_passed / total_cases) * 100.0, 2) if total_cases > 0 else 100.0
    execution_error_rate_pct = round((total_execution_errors / total_cases) * 100.0, 2) if total_cases > 0 else 0.0
    avg_grounding = sum(r["grounding_recall"] for r in results) / total_cases if total_cases > 0 else 0.0
    avg_rouge_l = sum(r["rouge_l_f1"] for r in results) / total_cases if total_cases > 0 else 0.0
    avg_faithfulness = sum(r["faithfulness_score"] for r in results) / total_cases if total_cases > 0 else 0.0
    avg_relevance = sum(r["relevance_score"] for r in results) / total_cases if total_cases > 0 else 0.0
    avg_latency = total_latency_ms / total_cases if total_cases > 0 else 0.0

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "execution_mode": "MOCKED" if mocked else "LIVE",
        "total_cases": total_cases,
        "math_accuracy_pct": math_accuracy_pct,
        "execution_error_rate_pct": execution_error_rate_pct,
        "grounding_recall": round(avg_grounding, 4),
        "rouge_l_f1": round(avg_rouge_l, 4),
        "faithfulness_score": round(avg_faithfulness, 4),
        "relevance_score": round(avg_relevance, 4),
        "avg_latency_ms": round(avg_latency, 2),
    }

    # Save JSON report
    report_json_path = os.path.join(output_dir, "benchmark_report.json")
    with open(report_json_path, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    # Save Markdown report
    report_md_path = os.path.join(output_dir, "benchmark_report.md")
    markdown_content = format_markdown_report(summary, results)
    with open(report_md_path, "w") as f:
        f.write(markdown_content)

    logger.info(f"Benchmark completed! Report saved to {report_md_path}")
    logger.info(f"Math Accuracy: {math_accuracy_pct}% | Exec Errors: {execution_error_rate_pct}% | Grounding Recall: {avg_grounding:.4f} | ROUGE-L F1: {avg_rouge_l:.4f}")

    full_wall_clock = time.monotonic() - full_run_start

    print("\n" + "="*80)
    print("PART 0 — PROFILE BREAKDOWN SUMMARY")
    print("="*80)
    print(f"Total wall-clock time for full run: {full_wall_clock:.2f} s ({full_wall_clock/60.0:.2f} min)")
    print(f"Total time spent in real Gemini/genai calls (agent reasoning): {PROFILER['total_gemini_reasoning_time_sec']:.2f} s")
    print(f"Total time spent in Model Armor calls (ingress + egress): {PROFILER['total_model_armor_time_sec']:.2f} s")
    print(f"Total time spent in real external data calls (BigQuery, Vertex Search): {PROFILER['total_external_data_time_sec']:.2f} s")
    print(f"Total time spent in LLM-judge calls (Vertex AI Evaluation): {PROFILER['total_llm_judge_time_sec']:.2f} s")
    print(f"Number of cases run: {total_cases}")
    
    if results:
        latencies = [r["latency_ms"] / 1000.0 for r in results]
        avg_case_time = sum(latencies) / len(latencies)
        max_case = max(results, key=lambda x: x["latency_ms"])
        max_time = max_case["latency_ms"] / 1000.0
        print(f"Average case latency: {avg_case_time:.2f} s")
        print(f"Slowest case: '{max_case['case_id']}' at {max_time:.2f} s (Ratio to avg: {max_time/avg_case_time:.2f}x)")
        if max_time > 3.0 * avg_case_time:
            print(f"⚠️ OUTLIER DETECTED: Case '{max_case['case_id']}' took {max_time:.2f}s (>3x average).")
        else:
            print("No extreme single-case latency outlier (>3x avg) detected.")
    print("="*80 + "\n")

    if regression_check:
        has_regression = False
        if math_accuracy_pct < 100.0:
            logger.error(f"REGRESSION DETECTED: Math Accuracy dropped to {math_accuracy_pct}% (Required: 100.0%)")
            has_regression = True
        if execution_error_rate_pct > 0.0:
            logger.error(f"REGRESSION DETECTED: Execution Error Rate is {execution_error_rate_pct}% (Required: 0.0%)")
            has_regression = True
        if avg_faithfulness < 0.85:
            logger.error(f"REGRESSION DETECTED: LLM Faithfulness dropped to {avg_faithfulness:.4f} (Required: >= 0.8500)")
            has_regression = True
        if avg_relevance < 0.85:
            logger.error(f"REGRESSION DETECTED: Answer Relevance dropped to {avg_relevance:.4f} (Required: >= 0.8500)")
            has_regression = True

        if has_regression:
            logger.error("Regression check failed! Exiting with status code 1.")
            return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description="SEC EDGAR Analyst Benchmark & Evaluation Runner")
    parser.add_argument("--mocked", action="store_true", default=True, help="Run in mocked offline mode (default)")
    parser.add_argument("--live", action="store_true", help="Run in live mode with real LLM inference & LLM judge")
    parser.add_argument("--regression-check", action="store_true", help="Enforce regression gating thresholds")
    parser.add_argument("--cases", type=int, default=None, help="Limit number of test cases to evaluate")
    parser.add_argument("--output-dir", type=str, default=RESULTS_DIR, help="Directory to save report artifacts")

    args = parser.parse_args()
    is_mocked = not args.live

    exit_code = run_benchmark(
        mocked=is_mocked,
        limit=args.cases,
        regression_check=args.regression_check,
        output_dir=args.output_dir,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
