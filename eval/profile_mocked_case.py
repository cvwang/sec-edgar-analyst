"""Fine-grained profiling script instrumenting every subphase of mocked-tier execution."""

import time
import json
import asyncio
from unittest.mock import patch, MagicMock

import google.genai.models
from google.genai import types
from google.adk.events import Event
from google.adk.models import LlmResponse

from agent.config import settings
from agent.guardrails.model_armor import ModelArmorGuard, model_armor_guard
from agent.observability.telemetry_sink import BigQueryTelemetrySink
from agent.root_orchestrator import (
    RootOrchestrator,
    calculate_financial_variance_tool,
    query_bigquery_financial_metrics_tool,
    search_tool,
    model_armor_before_model_callback,
    model_armor_after_model_callback,
    consolidate_grounded_chunks,
    reset_grounded_chunks,
)
from agent.rag.vertex_search import VertexAISearchClient, VertexSearchResult
from agent.rag.bigquery_store import BigQueryFinancialStore, FinancialMetricRecord
from agent.rag.sec_corpus import SECCorpusStore
from app.app_controller import AppController
from eval.evaluator import EvalEngine
from eval.run_benchmark import (
    mock_search_filings_boundary,
    mock_query_metrics_boundary,
    mock_genai_generate_content_boundary,
    CURRENT_EVAL_CASE,
)

# Stopwatch metrics
TIMINGS = {
    "llm_mock_async_generate": 0.0,
    "llm_mock_sync_generate": 0.0,
    "model_armor_ingress": 0.0,
    "model_armor_egress": 0.0,
    "tool_calc_variance": 0.0,
    "tool_bigquery_lookup": 0.0,
    "tool_sec_search": 0.0,
    "rag_highlight_and_consolidation": 0.0,
    "evaluator_scoring": 0.0,
    "adk_runner_loop_and_otel": 0.0,
    "total_wall_clock": 0.0,
}

# Instrument LLM mocks
orig_mock_genai = mock_genai_generate_content_boundary
async def timed_mock_async_generate(self, model, contents, config=None):
    t0 = time.perf_counter()
    res = await orig_mock_genai(self, model, contents, config)
    TIMINGS["llm_mock_async_generate"] += (time.perf_counter() - t0) * 1000.0
    return res

def timed_mock_sync_generate(self, model, contents, config=None):
    t0 = time.perf_counter()
    res = types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    parts=[types.Part.from_text(text="Apple Inc. reported Total Net Sales of $383,285 million in FY2023.")],
                    role="model",
                )
            )
        ]
    )
    TIMINGS["llm_mock_sync_generate"] += (time.perf_counter() - t0) * 1000.0
    return res

# Instrument Model Armor
orig_sanitize_user = ModelArmorGuard.sanitize_user_prompt
def timed_sanitize_user(self, prompt: str):
    t0 = time.perf_counter()
    res = orig_sanitize_user(self, prompt)
    TIMINGS["model_armor_ingress"] += (time.perf_counter() - t0) * 1000.0
    return res

orig_sanitize_model = ModelArmorGuard.sanitize_model_response
def timed_sanitize_model(self, model_response_text: str):
    t0 = time.perf_counter()
    res = orig_sanitize_model(self, model_response_text)
    TIMINGS["model_armor_egress"] += (time.perf_counter() - t0) * 1000.0
    return res

# Instrument Tools
orig_calc = calculate_financial_variance_tool
def timed_calc(*args, **kwargs):
    t0 = time.perf_counter()
    res = orig_calc(*args, **kwargs)
    TIMINGS["tool_calc_variance"] += (time.perf_counter() - t0) * 1000.0
    return res

orig_bq = BigQueryFinancialStore.query_metrics
def timed_bq(self, ticker: str, fiscal_year: int):
    t0 = time.perf_counter()
    res = mock_query_metrics_boundary(self, ticker, fiscal_year)
    TIMINGS["tool_bigquery_lookup"] += (time.perf_counter() - t0) * 1000.0
    return res

orig_search = VertexAISearchClient.search_filings
def timed_search(self, query: str, page_size: int = 5):
    t0 = time.perf_counter()
    res = mock_search_filings_boundary(self, query, page_size)
    TIMINGS["tool_sec_search"] += (time.perf_counter() - t0) * 1000.0
    return res

def profile_single_case():
    with open("eval/golden_dataset.json") as f:
        cases = json.load(f)
    
    case = [c for c in cases if c["case_id"] == "test_001_aapl_revenue"][0]
    CURRENT_EVAL_CASE["current"] = case

    # Apply instrumentations
    settings.model_armor_offline_mode = True
    model_armor_guard.offline_mode = True

    with patch.object(google.genai.models.AsyncModels, "generate_content", timed_mock_async_generate), \
         patch.object(google.genai.models.Models, "generate_content", timed_mock_sync_generate), \
         patch.object(ModelArmorGuard, "sanitize_user_prompt", timed_sanitize_user), \
         patch.object(ModelArmorGuard, "sanitize_model_response", timed_sanitize_model), \
         patch.object(BigQueryFinancialStore, "query_metrics", timed_bq), \
         patch.object(VertexAISearchClient, "search_filings", timed_search), \
         patch.object(BigQueryTelemetrySink, "log_event", lambda *args, **kwargs: None):

        controller = AppController()
        prompt = f"Analyze {case['ticker']} {case['metric_name']} for {case['current_year']} compared to {case['prior_year']}"
        session_id = "profiling_session_001"

        t_wall_start = time.perf_counter()
        
        # Step 1: Execute Orchestration
        t_orch_start = time.perf_counter()
        resp = controller.dispatch_query(prompt=prompt, session_id=session_id)
        t_orch_end = time.perf_counter()

        # Step 2: Evaluation Scoring
        evaluator = EvalEngine()
        retrieved_chunks = [
            c.get("content") or c.get("snippet") if isinstance(c, dict) else (c.snippet if hasattr(c, "snippet") else str(c))
            for c in resp.get("retrieved_context", [])
        ]
        if not retrieved_chunks:
            retrieved_chunks = [f"{case['ticker']} Item 7 MD&A: {case.get('reference_explanation', '')}"]

        t_eval_start = time.perf_counter()
        eval_res = evaluator.evaluate_case_full(
            case=case,
            generated_narrative=resp.get("narrative", ""),
            retrieved_chunks=retrieved_chunks,
            run_llm_judge=False,
            structured_tool_result=resp.get("variance_result"),
        )
        t_eval_end = time.perf_counter()
        TIMINGS["evaluator_scoring"] = (t_eval_end - t_eval_start) * 1000.0

        t_wall_end = time.perf_counter()
        TIMINGS["total_wall_clock"] = (t_wall_end - t_wall_start) * 1000.0

        total_accounted = (
            TIMINGS["llm_mock_async_generate"] +
            TIMINGS["llm_mock_sync_generate"] +
            TIMINGS["model_armor_ingress"] +
            TIMINGS["model_armor_egress"] +
            TIMINGS["tool_calc_variance"] +
            TIMINGS["tool_bigquery_lookup"] +
            TIMINGS["tool_sec_search"] +
            TIMINGS["evaluator_scoring"]
        )
        TIMINGS["adk_runner_loop_and_otel"] = max(0.0, TIMINGS["total_wall_clock"] - total_accounted)

        print("\n" + "="*80)
        print(f"FINE-GRAINED PROFILING REPORT: SINGLE MOCKED CASE ('{case['case_id']}')")
        print("="*80)
        print(f"1. LLM Mock Execution (AsyncModels.generate_content)       : {TIMINGS['llm_mock_async_generate']:8.3f} ms ({TIMINGS['llm_mock_async_generate']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"2. LLM Mock Highlighting (Models.generate_content sync)    : {TIMINGS['llm_mock_sync_generate']:8.3f} ms ({TIMINGS['llm_mock_sync_generate']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"3. Model Armor Ingress Screening (Offline Regex Guard)      : {TIMINGS['model_armor_ingress']:8.3f} ms ({TIMINGS['model_armor_ingress']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"4. Model Armor Egress Screening (Offline Regex Guard)       : {TIMINGS['model_armor_egress']:8.3f} ms ({TIMINGS['model_armor_egress']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"5. Tool Execution (calculate_financial_variance_tool)       : {TIMINGS['tool_calc_variance']:8.3f} ms ({TIMINGS['tool_calc_variance']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"6. Tool Execution (BigQuery Financial Metric Store Mock)    : {TIMINGS['tool_bigquery_lookup']:8.3f} ms ({TIMINGS['tool_bigquery_lookup']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"7. Tool Execution (Vertex AI Search Filing Chunks Mock)     : {TIMINGS['tool_sec_search']:8.3f} ms ({TIMINGS['tool_sec_search']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"8. Evaluator Scoring (Layer 1 Deterministic & Math Checks)  : {TIMINGS['evaluator_scoring']:8.3f} ms ({TIMINGS['evaluator_scoring']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print(f"9. ADK Runner Engine, Event Loop & OpenTelemetry Tracing    : {TIMINGS['adk_runner_loop_and_otel']:8.3f} ms ({TIMINGS['adk_runner_loop_and_otel']/TIMINGS['total_wall_clock']*100:5.1f}%)")
        print("-" * 80)
        print(f"TOTAL MEASURED WALL-CLOCK LATENCY                           : {TIMINGS['total_wall_clock']:8.3f} ms (100.0%)")
        print("="*80 + "\n")

if __name__ == "__main__":
    profile_single_case()
