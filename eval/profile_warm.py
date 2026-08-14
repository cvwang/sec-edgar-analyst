"""Measure every single subphase inside RootOrchestrator.run_analysis."""

import time
import json
from unittest.mock import patch

import google.genai.models
from google.genai import types

from agent.config import settings
from agent.guardrails.model_armor import ModelArmorGuard, model_armor_guard
from agent.observability.telemetry_sink import BigQueryTelemetrySink
from agent.rag.vertex_search import VertexAISearchClient
from agent.rag.bigquery_store import BigQueryFinancialStore
from app.app_controller import AppController
from eval.run_benchmark import (
    mock_search_filings_boundary,
    mock_query_metrics_boundary,
    mock_genai_generate_content_boundary,
    CURRENT_EVAL_CASE,
)

async def mock_async_generate(self, model, contents, config=None):
    return await mock_genai_generate_content_boundary(self, model, contents, config)

def mock_sync_generate(self, model, contents, config=None):
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

def profile_inner_steps():
    with open("eval/golden_dataset.json") as f:
        cases = json.load(f)
    case = [c for c in cases if c["case_id"] == "test_001_aapl_revenue"][0]
    CURRENT_EVAL_CASE["current"] = case

    settings.model_armor_offline_mode = True
    model_armor_guard.offline_mode = True

    with patch.object(google.genai.models.AsyncModels, "generate_content", mock_async_generate), \
         patch.object(google.genai.models.Models, "generate_content", mock_sync_generate), \
         patch.object(BigQueryFinancialStore, "query_metrics", mock_query_metrics_boundary), \
         patch.object(VertexAISearchClient, "search_filings", mock_search_filings_boundary), \
         patch.object(BigQueryTelemetrySink, "log_event", lambda *args, **kwargs: None):

        controller = AppController()
        prompt = f"Analyze {case['ticker']} {case['metric_name']} for {case['current_year']} compared to {case['prior_year']}"

        # Warm up JIT / module imports
        controller.dispatch_query(prompt=prompt, session_id="warmup_session")

        # Now measure pure execution time on a fresh session
        t0 = time.perf_counter()
        resp = controller.dispatch_query(prompt=prompt, session_id="timed_session")
        t1 = time.perf_counter()

        print(f"Warm execution total time: {(t1 - t0)*1000.0:.2f} ms")
        print(f"Reported latency_ms in response: {resp.get('latency_ms', 0):.2f} ms")

if __name__ == "__main__":
    profile_inner_steps()
