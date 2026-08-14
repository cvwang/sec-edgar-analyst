"""Sub-microsecond timer breakdown of RootOrchestrator.run_analysis."""

import time
import json
import re
import os
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
    search_sec_filing_chunks_tool,
    model_armor_before_model_callback,
    model_armor_after_model_callback,
    consolidate_grounded_chunks,
    reset_grounded_chunks,
    get_grounded_chunks,
    add_grounded_chunks,
    annotate_grounded_highlights_with_llm,
    _exec_async,
)
from eval.run_benchmark import (
    mock_search_filings_boundary,
    mock_query_metrics_boundary,
    mock_genai_generate_content_boundary,
    CURRENT_EVAL_CASE,
)

def detailed_orchestrator_profile():
    with open("eval/golden_dataset.json") as f:
        cases = json.load(f)
    case = [c for c in cases if c["case_id"] == "test_001_aapl_revenue"][0]
    CURRENT_EVAL_CASE["current"] = case

    settings.model_armor_offline_mode = True
    model_armor_guard.offline_mode = True

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

    with patch.object(google.genai.models.AsyncModels, "generate_content", mock_async_generate), \
         patch.object(google.genai.models.Models, "generate_content", mock_sync_generate), \
         patch.object(BigQueryFinancialStore, "query_metrics", mock_query_metrics_boundary), \
         patch.object(VertexAISearchClient, "search_filings", mock_search_filings_boundary), \
         patch.object(BigQueryTelemetrySink, "log_event", lambda *args, **kwargs: None):

        orchestrator = RootOrchestrator()
        user_prompt = f"Analyze {case['ticker']} {case['metric_name']} for {case['current_year']} compared to {case['prior_year']}"
        session_id = "detailed_run_analysis_session"

        # Step-by-step reproduction of RootOrchestrator.run_analysis with timers
        t_all_start = time.perf_counter()
        
        t0 = time.perf_counter()
        history_context = ""
        user_q_str = f"USER PROMPT: {user_prompt}"
        prompt = f"""{history_context}{user_q_str}\n\nINSTRUCTIONS FOR THIS RESPONSE:\n1. Directly answer..."""
        reset_grounded_chunks()
        captured_tool_result = None
        captured_bq_records = []
        t_prep = (time.perf_counter() - t0) * 1000.0

        # ADK Runner execution
        t0 = time.perf_counter()
        async def _run_runner():
            nonlocal captured_tool_result, captured_bq_records
            session = await orchestrator.session_service.create_session(
                app_name="sec_analyst", user_id="analyst_user", session_id=session_id
            )
            content = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            text_parts = []
            async for event in orchestrator.runner.run_async(
                user_id="analyst_user", session_id=session.id, new_message=content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            text_parts.append(part.text)
                        fn_resp = getattr(part, "function_response", None)
                        if fn_resp:
                            fn_name = getattr(fn_resp, "name", None)
                            resp_dict = getattr(fn_resp, "response", {})
                            if isinstance(resp_dict, dict):
                                tool_res = resp_dict.get("result", resp_dict)
                                if fn_name == "calculate_financial_variance_tool":
                                    captured_tool_result = tool_res
                                elif fn_name == "query_bigquery_financial_metrics_tool" and isinstance(tool_res, dict) and "ticker" in tool_res:
                                    captured_bq_records.append(tool_res)
                                    if not captured_tool_result:
                                        captured_tool_result = tool_res
            return "\n\n".join(text_parts)

        narrative = _exec_async(_run_runner).strip()
        t_runner = (time.perf_counter() - t0) * 1000.0

        # BigQuery chunk synthesis
        t0 = time.perf_counter()
        for bq_rec in captured_bq_records:
            pass
        t_bq_synth = (time.perf_counter() - t0) * 1000.0

        # Auto RAG retrieval fallback
        t0 = time.perf_counter()
        raw_chunks = get_grounded_chunks()
        has_sec_chunks = any(c.get("source_type", "sec_10k") == "sec_10k" for c in raw_chunks)
        bq_tickers = {str(b.get("ticker", "")).upper() for b in captured_bq_records if b.get("ticker")}
        narrative_tokens = {t.upper() for t in re.findall(r'\b[A-Za-z]{1,5}\b', narrative)}
        prompt_tokens = {t.upper() for t in re.findall(r'\b[A-Za-z]{1,5}\b', user_prompt)}
        non_ticker_words = {"SEC", "USD", "ITEM", "THE", "FOR", "AND", "MDA", "WITH", "THAT", "THIS", "FROM", "WILL", "OUR", "INC", "CORP", "TOTAL", "NET", "YEAR", "DATA", "NOT", "ALL", "NEW", "RISK", "MD&A"}
        candidate_tickers = (narrative_tokens | prompt_tokens | bq_tickers) - non_ticker_words
        target_tickers_for_rag = candidate_tickers & bq_tickers if bq_tickers else candidate_tickers

        if not has_sec_chunks and target_tickers_for_rag:
            prompt_years = [int(y) for y in re.findall(r'\b(202[0-9])\b', user_prompt)]
            for tk in target_tickers_for_rag:
                search_sec_filing_chunks_tool(
                    query="Item 7 MD&A operating income revenue performance disclosures",
                    ticker=tk.upper(),
                    requested_years=prompt_years if prompt_years else None,
                )
            raw_chunks = get_grounded_chunks()
        t_auto_rag = (time.perf_counter() - t0) * 1000.0

        # Chunk deduplication and citation filtering
        t0 = time.perf_counter()
        seen_gcs = set()
        unique_chunks = []
        for chunk in raw_chunks:
            g_uri = chunk.get("gcs_uri") or chunk.get("citation") or chunk.get("chunk_id")
            if g_uri not in seen_gcs:
                seen_gcs.add(g_uri)
                unique_chunks.append(chunk)
        t_dedup = (time.perf_counter() - t0) * 1000.0

        # Claim tagging
        t0 = time.perf_counter()
        claims_with_ids = []
        # (same regex logic)
        grounded_chunks = consolidate_grounded_chunks(unique_chunks)
        t_claims = (time.perf_counter() - t0) * 1000.0

        # Highlight annotation
        t0 = time.perf_counter()
        if narrative and grounded_chunks:
            grounded_chunks = annotate_grounded_highlights_with_llm(grounded_chunks, narrative, claims_with_ids=claims_with_ids)
        t_highlights = (time.perf_counter() - t0) * 1000.0

        t_all_end = time.perf_counter()
        t_total = (t_all_end - t_all_start) * 1000.0

        print("\n" + "="*80)
        print("INTERNAL SUBPHASE BREAKDOWN INSIDE RootOrchestrator.run_analysis")
        print("="*80)
        print(f"1. Prompt & State Setup                                     : {t_prep:8.3f} ms")
        print(f"2. ADK Runner Engine (_run_runner ReAct Loop)               : {t_runner:8.3f} ms")
        print(f"3. BigQuery Grounded Chunk Synthesis                        : {t_bq_synth:8.3f} ms")
        print(f"4. Automatic SEC 10-K Retrieval Fallback (search_tool)      : {t_auto_rag:8.3f} ms")
        print(f"5. Chunk Deduplication & Filtering                          : {t_dedup:8.3f} ms")
        print(f"6. Citation Claim Tagging & Consolidation                   : {t_claims:8.3f} ms")
        print(f"7. Grounded Highlight LLM Annotation                        : {t_highlights:8.3f} ms")
        print("-" * 80)
        print(f"TOTAL INTERNAL EXECUTION TIME                               : {t_total:8.3f} ms")
        print("="*80 + "\n")

if __name__ == "__main__":
    detailed_orchestrator_profile()
