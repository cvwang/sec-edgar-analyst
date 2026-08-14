"""Full timer breakdown of a single benchmark case in eval/run_benchmark.py."""

import time
import json
import asyncio
from unittest.mock import patch

import google.genai.models
from google.genai import types

from agent.config import settings
from agent.guardrails.model_armor import ModelArmorGuard, model_armor_guard
from agent.observability.telemetry_sink import BigQueryTelemetrySink
from agent.rag.vertex_search import VertexAISearchClient
from agent.rag.bigquery_store import BigQueryFinancialStore
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
from app.app_controller import AppController
from eval.evaluator import EvalEngine
from eval.run_benchmark import (
    mock_search_filings_boundary,
    mock_query_metrics_boundary,
    mock_genai_generate_content_boundary,
    CURRENT_EVAL_CASE,
)

def run_profile():
    with open("eval/golden_dataset.json") as f:
        cases = json.load(f)
    case = [c for c in cases if c["case_id"] == "test_001_aapl_revenue"][0]
    CURRENT_EVAL_CASE["current"] = case

    settings.model_armor_offline_mode = True
    model_armor_guard.offline_mode = True

    # Instrument every phase
    timer = {}

    def time_block(label):
        class Context:
            def __enter__(self):
                self.t0 = time.perf_counter()
                return self
            def __exit__(self, *args):
                elapsed = (time.perf_counter() - self.t0) * 1000.0
                timer[label] = timer.get(label, 0.0) + elapsed
        return Context()

    async def timed_async_generate(self, model, contents, config=None):
        with time_block("LLM Async Generate Content (Mock)"):
            return await mock_genai_generate_content_boundary(self, model, contents, config)

    def timed_sync_generate(self, model, contents, config=None):
        with time_block("LLM Sync Generate Content (Highlight Annotator Mock)"):
            return types.GenerateContentResponse(
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[types.Part.from_text(text="Apple Inc. reported Total Net Sales of $383,285 million in FY2023.")],
                            role="model",
                        )
                    )
                ]
            )

    orig_user_prompt = ModelArmorGuard.sanitize_user_prompt
    def timed_user_prompt(self, prompt: str):
        with time_block("Model Armor Ingress Screening (Offline)"):
            return orig_user_prompt(self, prompt)

    orig_model_resp = ModelArmorGuard.sanitize_model_response
    def timed_model_resp(self, resp: str):
        with time_block("Model Armor Egress Screening (Offline)"):
            return orig_model_resp(self, resp)

    orig_calc = calculate_financial_variance_tool
    def timed_calc(*args, **kwargs):
        with time_block("calculate_financial_variance_tool"):
            return orig_calc(*args, **kwargs)

    orig_bq = BigQueryFinancialStore.query_metrics
    def timed_bq(self, ticker: str, fiscal_year: int):
        with time_block("BigQuery Financial Store Lookup (Mock)"):
            return mock_query_metrics_boundary(self, ticker, fiscal_year)

    orig_search = VertexAISearchClient.search_filings
    def timed_search(self, query: str, page_size: int = 5):
        with time_block("Vertex AI Search Filing Chunks (Mock)"):
            return mock_search_filings_boundary(self, query, page_size)

    with patch.object(google.genai.models.AsyncModels, "generate_content", timed_async_generate), \
         patch.object(google.genai.models.Models, "generate_content", timed_sync_generate), \
         patch.object(ModelArmorGuard, "sanitize_user_prompt", timed_user_prompt), \
         patch.object(ModelArmorGuard, "sanitize_model_response", timed_model_resp), \
         patch.object(BigQueryFinancialStore, "query_metrics", timed_bq), \
         patch.object(VertexAISearchClient, "search_filings", timed_search), \
         patch.object(BigQueryTelemetrySink, "log_event", lambda *args, **kwargs: None):

        t_total_start = time.perf_counter()

        with time_block("AppController & RootOrchestrator Initialization"):
            controller = AppController()

        prompt = f"Analyze {case['ticker']} {case['metric_name']} for {case['current_year']} compared to {case['prior_year']}"
        session_id = "profiling_session_breakdown"

        with time_block("RootOrchestrator Total Execution"):
            resp = controller.dispatch_query(prompt=prompt, session_id=session_id)

        with time_block("Benchmark Evaluation Scoring (Deterministic & Math)"):
            evaluator = EvalEngine()
            retrieved_chunks = [
                c.get("content") or c.get("snippet") if isinstance(c, dict) else (c.snippet if hasattr(c, "snippet") else str(c))
                for c in resp.get("retrieved_context", [])
            ]
            if not retrieved_chunks:
                retrieved_chunks = [f"{case['ticker']} Item 7 MD&A: {case.get('reference_explanation', '')}"]

            eval_res = evaluator.evaluate_case_full(
                case=case,
                generated_narrative=resp.get("narrative", ""),
                retrieved_chunks=retrieved_chunks,
                run_llm_judge=False,
                structured_tool_result=resp.get("variance_result"),
            )

        t_total_end = time.perf_counter()
        total_time = (t_total_end - t_total_start) * 1000.0

        print("\n" + "="*85)
        print("EXACT TIMER BREAKDOWN OF SINGLE MOCKED BENCHMARK CASE ('test_001_aapl_revenue')")
        print("="*85)
        for k, v in timer.items():
            print(f"  • {k:<60}: {v:8.3f} ms ({v/total_time*100:5.1f}%)")
        print("-" * 85)
        print(f"  TOTAL CASE WALL-CLOCK TIME                                    : {total_time:8.3f} ms (100.0%)")
        print("="*85 + "\n")

if __name__ == "__main__":
    run_profile()
