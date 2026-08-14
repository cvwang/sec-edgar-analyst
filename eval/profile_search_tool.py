"""Profile inside search_sec_filing_chunks_tool."""

import time
from unittest.mock import patch
from agent.rag.sec_corpus import SECCorpusStore, formulate_vertex_search_query, clean_sec_document_text, extract_relevant_excerpt, search_sec_filing_chunks_tool
from agent.rag.vertex_search import VertexAISearchClient
from eval.run_benchmark import mock_search_filings_boundary

with patch.object(VertexAISearchClient, "search_filings", mock_search_filings_boundary):
    t0 = time.perf_counter()
    store = SECCorpusStore()
    t1 = time.perf_counter()
    print(f"SECCorpusStore() init time: {(t1 - t0)*1000.0:.2f} ms")

    t0 = time.perf_counter()
    q = formulate_vertex_search_query(query="Item 7 MD&A operating income revenue performance disclosures", ticker="AAPL", requested_years=[2023])
    t1 = time.perf_counter()
    print(f"formulate_vertex_search_query: {(t1 - t0)*1000.0:.2f} ms")

    t0 = time.perf_counter()
    res = store.vertex_search.search_filings(q, page_size=5)
    t1 = time.perf_counter()
    print(f"store.vertex_search.search_filings: {(t1 - t0)*1000.0:.2f} ms")

    t0 = time.perf_counter()
    for vr in res:
        c = clean_sec_document_text(vr.snippet)
    t1 = time.perf_counter()
    print(f"clean_sec_document_text: {(t1 - t0)*1000.0:.2f} ms")

    t0 = time.perf_counter()
    for vr in res:
        e = extract_relevant_excerpt(vr.snippet, q)
    t1 = time.perf_counter()
    print(f"extract_relevant_excerpt: {(t1 - t0)*1000.0:.2f} ms")

    t0 = time.perf_counter()
    chunks = search_sec_filing_chunks_tool(query="Item 7 MD&A operating income revenue performance disclosures", ticker="AAPL", requested_years=[2023])
    t1 = time.perf_counter()
    print(f"search_sec_filing_chunks_tool total: {(t1 - t0)*1000.0:.2f} ms")
