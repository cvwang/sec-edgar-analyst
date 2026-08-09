"""Unit and Integration Evaluation Tests for RAG-06 SEC Corpus Formatting & Retrieval."""

import pytest
from agent.rag.sec_corpus import (
    clean_sec_document_text,
    annotate_text_with_clauses,
    extract_relevant_excerpt,
    formulate_vertex_search_query,
    SECDocumentChunk,
    SECCorpusStore,
)


def test_clean_sec_document_text_html_entity_decoding():
    """Verifies that clean_sec_document_text decodes HTML entities into proper clean characters."""
    raw = "Tesla&#8217;s revenue &#8220;increased&#8221; by 15% &#8212; &nbsp;operating margin &amp; cash flow expanded."
    cleaned = clean_sec_document_text(raw)
    assert "Tesla's revenue \"increased\" by 15% — operating margin & cash flow expanded." in cleaned
    assert "&#8220;" not in cleaned
    assert "&nbsp;" not in cleaned


def test_clean_sec_document_text_preamble_stripping():
    """Verifies dataset header preambles and source URLs are stripped."""
    raw = """# REAL UNABRIDGED SEC EDGAR FILING: Tesla, Inc. (TSLA) - FY2023 10-K
## Source URL: https://www.sec.gov/Archives/edgar/data/1318605/000162828024002390/tsla-20231231.htm
## Section: Item 1A - Risk Factors

Operational challenges impacted production."""

    cleaned = clean_sec_document_text(raw)
    assert "REAL UNABRIDGED SEC EDGAR FILING" not in cleaned
    assert "Source URL" not in cleaned
    assert "Operational challenges impacted production." in cleaned


def test_clean_sec_document_text_markdown_headings():
    """Verifies ITEM section headers are structured into Markdown headings."""
    raw = "ITEM 1A. RISK FACTORS We face competitive risks in automotive manufacturing."
    cleaned = clean_sec_document_text(raw)
    assert "# Item 1A. Risk Factors" in cleaned
    assert "We face competitive risks in automotive manufacturing." in cleaned

    raw_mda = "ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION Results of operations were strong."
    cleaned_mda = clean_sec_document_text(raw_mda)
    assert "# Item 7. Management's Discussion and Analysis (MD&A)" in cleaned_mda


def test_clean_sec_document_text_bullet_list_formatting():
    """Verifies list markers like •, (a), (b), (i) are formatted into Markdown bullet items."""
    raw = "Risks include: (a) Supply chain disruption. (b) Regulatory compliance changes. (c) Battery raw material costs."
    cleaned = clean_sec_document_text(raw)
    assert "- Supply chain disruption." in cleaned
    assert "- Regulatory compliance changes." in cleaned
    assert "- Battery raw material costs." in cleaned


def test_annotate_text_with_clauses():
    """Verifies sentence highlighting wraps exact substantiating clauses in <mark> tags."""
    content = "Revenue increased 15% to $96.7B. Automotive gross margin was 18.2%. R&D investments expanded."
    clauses = ["Automotive gross margin was 18.2%."]

    annotated = annotate_text_with_clauses(content, clauses)
    assert "<mark>Automotive gross margin was 18.2%.</mark>" in annotated


def test_extract_relevant_excerpt():
    """Verifies extract_relevant_excerpt returns focused snippets around analytical terms."""
    content = "The company reported operating revenue of $50 billion for the fiscal year. Risk factors remain low. Capital expenditures were $3B."
    snippet = extract_relevant_excerpt(content, query_context="revenue operating")
    assert "revenue" in snippet.lower()
    assert len(snippet) <= 400


def test_sec_document_chunk_model():
    """Verifies SECDocumentChunk model validation and payload serialization."""
    chunk = SECDocumentChunk(
        chunk_id="chunk_1",
        ticker="TSLA",
        company_name="Tesla, Inc.",
        fiscal_year=2023,
        section="Item 1A - Risk Factors",
        content="Automotive production risks.",
        highlight_excerpt="<mark>Automotive production risks.</mark>",
        citation="Vertex AI Search (sec-10k-filings-datastore) [gs://sec-analyst-sec-reports/filings/TSLA_2023_Item1A_Risk.md]",
        gcs_uri="gs://sec-analyst-sec-reports/filings/TSLA_2023_Item1A_Risk.md",
    )
    dumped = chunk.model_dump()
    assert dumped["ticker"] == "TSLA"
    assert dumped["fiscal_year"] == 2023
    assert "<mark>" in dumped["highlight_excerpt"]
    assert "Vertex AI Search" in dumped["citation"]
