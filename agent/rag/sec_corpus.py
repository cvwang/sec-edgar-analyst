"""SEC 10-K Document Corpus Store for Item 7 MD&A and Item 1A Risk Factors disclosures.

Grounded exclusively in Google Cloud Storage (gs://sec-analyst-sec-reports/filings/) and GCP Vertex AI Search.
Zero local disk dependencies.

Feature (RAG-06): SEC corpus filing chunks are formatted with clean Markdown/HTML structural formatting
for enhanced rendering in the UI split-pane context drawer.
"""

import os
import re
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from agent.rag.vertex_search import VertexAISearchClient

GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "sec-analyst-sec-reports")

_request_grounded_chunks: List[dict] = []


def reset_grounded_chunks():
    global _request_grounded_chunks
    _request_grounded_chunks = []


def get_grounded_chunks() -> List[dict]:
    global _request_grounded_chunks
    return list(_request_grounded_chunks)


def add_grounded_chunks(chunks: List[dict]):
    global _request_grounded_chunks
    _request_grounded_chunks.extend(chunks)


def annotate_text_with_clauses(content: str, marked_clauses: list) -> str:
    """Wraps exact or matching sentence blocks in <mark> tags inside content."""
    if not content or not marked_clauses:
        return content

    annotated = content
    for clause in marked_clauses:
        clause_clean = clause.strip()
        if not clause_clean or len(clause_clean) < 8:
            continue

        if f"<mark>{clause_clean}</mark>" in annotated:
            continue

        if clause_clean in annotated:
            annotated = annotated.replace(clause_clean, f"<mark>{clause_clean}</mark>")
            continue

        # Try sentence-level matching if Gemini modified minor words or capitalization
        sentences = re.split(r'(?<=[.!?])\s+', annotated)
        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean) < 15 or "<mark>" in s:
                continue

            words = [w for w in re.findall(r'\b[A-Za-z0-9\$\.]+\b', clause_clean) if len(w) > 3]
            match_count = sum(1 for w in words if w in s_clean)
            if words and (match_count / len(words)) >= 0.5:
                annotated = annotated.replace(s_clean, f"<mark>{s_clean}</mark>")
                break

    return annotated


def fallback_sentence_highlight(content: str, narrative: str) -> str:
    """Deterministically finds the sentence in content with maximum keyword overlap with narrative and wraps it in <mark>."""
    if not content:
        return content

    if "<mark>" in content:
        return content

    sentences = re.split(r'(?<=[.!?])\s+', content)
    if not sentences:
        return f"<mark>{content[:300]}</mark>"

    stop_words = {"this", "that", "with", "from", "were", "have", "been", "which", "their", "there", "about", "other", "under", "will", "would", "could", "should"}
    narrative_words = set(
        w.lower() for w in re.findall(r'\b[A-Za-z0-9]{4,}\b', narrative)
        if w.lower() not in stop_words
    )

    best_sentence = None
    best_score = -1

    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) < 15:
            continue
        s_words = set(w.lower() for w in re.findall(r'\b[A-Za-z0-9]{4,}\b', s_clean))
        score = len(s_words.intersection(narrative_words))
        if score > best_score:
            best_score = score
            best_sentence = s_clean

    if best_sentence and best_sentence in content:
        return content.replace(best_sentence, f"<mark>{best_sentence}</mark>")

    # Fallback to the first non-trivial sentence
    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) >= 20 and s_clean in content:
            return content.replace(s_clean, f"<mark>{s_clean}</mark>")

    return f"<mark>{content[:300]}</mark>"


def derive_highlight_excerpt_from_content(content: str) -> str:
    """Extracts a focused 250-400 character excerpt around the <mark> tag in content."""
    if not content:
        return ""

    if "<mark>" not in content:
        return content[:350]

    mark_idx = content.find("<mark>")
    end_mark_idx = content.find("</mark>", mark_idx)
    if end_mark_idx == -1:
        end_mark_idx = mark_idx + 100
    else:
        end_mark_idx += 7  # include len("</mark>")

    start = max(0, mark_idx - 80)
    end = min(len(content), end_mark_idx + 120)

    excerpt = content[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(content):
        excerpt = excerpt + "..."

    return excerpt


def annotate_grounded_highlights_with_llm(chunks: List[dict], narrative: str) -> List[dict]:
    """Uses Vertex AI (Gemini Flash) in parallel to identify exact supporting sentence blocks and wrap them in <mark> tags."""
    if not chunks or not narrative:
        return chunks

    import concurrent.futures

    try:
        from google import genai
        from agent.config import settings

        client = genai.Client()
        fast_model = getattr(settings, "fast_model", "gemini-2.5-flash")

        def _annotate_single_chunk(chunk: dict) -> dict:
            raw_text = chunk.get("content", "")
            if not raw_text:
                return chunk

            prompt = f"""You are an SEC filing grounding specialist. Given the SEC 10-K filing excerpt and the AI Analyst Narrative below, identify 1 to 3 exact verbatim sentence blocks or key clauses directly from the SEC 10-K filing excerpt that directly ground or substantiate the claims in the narrative.

CRITICAL INSTRUCTIONS:
1. Extract ONLY verbatim sentence blocks or clauses directly present in the SEC 10-K FILING EXCERPT below.
2. Return each verbatim sentence block or clause enclosed inside <mark> and </mark> tags.
3. Do NOT rephrase, summarize, translate, or alter any words from the original filing excerpt text.
4. Output ONLY the <mark>quote</mark> blocks, separated by newlines.

SEC 10-K FILING EXCERPT:
{raw_text[:3000]}

ANALYST NARRATIVE:
{narrative[:1500]}
"""

            try:
                response = client.models.generate_content(
                    model=fast_model,
                    contents=prompt,
                )

                if response and response.text:
                    annotated = response.text.strip()
                    marked_clauses = re.findall(r'<mark>(.*?)</mark>', annotated, flags=re.DOTALL)
                    if marked_clauses:
                        chunk["content"] = annotate_text_with_clauses(chunk["content"], marked_clauses)
            except Exception as e:
                logging.warning(f"Single chunk annotation error: {e}")

            # Ensure content has <mark> tag via deterministic fallback if LLM missed it
            chunk["content"] = fallback_sentence_highlight(chunk["content"], narrative)

            # Derive highlight_excerpt directly from content around <mark> tag
            chunk["highlight_excerpt"] = derive_highlight_excerpt_from_content(chunk["content"])

            return chunk

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(chunks), 5)) as executor:
            annotated_chunks = list(executor.map(_annotate_single_chunk, chunks))

        return annotated_chunks
    except Exception as err:
        logging.warning(f"LLM grounded highlighting fallback: {err}")
        for chunk in chunks:
            chunk["content"] = fallback_sentence_highlight(chunk.get("content", ""), narrative)
            chunk["highlight_excerpt"] = derive_highlight_excerpt_from_content(chunk["content"])

    return chunks


def extract_relevant_excerpt(raw_content: str, query_context: str = "") -> str:
    """Extracts a focused 200-350 character relevant snippet around key financial/risk terms."""
    if not raw_content:
        return ""

    # Clean out heavy SEC headers and GCS file preambles
    clean = re.sub(r'#+\s*(?:REAL UNABRIDGED|Source URL|Section:)[^\n]*\n?', '', raw_content)
    clean = re.sub(r'https?://[^\s]+', '', clean)
    clean = re.sub(r'&\#\d+;', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()

    if len(clean) <= 300:
        return clean

    # Look for sentences containing financial/analytical terms
    keywords = ["revenue", "margin", "gross", "operating", "expense", "r&d", "sg&a", "risk", "increase", "decrease", "profit", "cash"]
    if query_context:
        extra_terms = [w.lower() for w in re.findall(r'\b[A-Za-z]{3,}\b', query_context) if w.lower() not in ["the", "and", "for", "with", "that", "this"]]
        keywords.extend(extra_terms)

    sentences = re.split(r'(?<=[.!?])\s+', clean)
    best_sentences = []
    current_len = 0

    for s in sentences:
        s_lower = s.lower()
        if any(k in s_lower for k in keywords):
            best_sentences.append(s)
            current_len += len(s)
            if current_len >= 250:
                break

    if best_sentences:
        return " ".join(best_sentences)[:400]

    # Fallback to first 300 characters of cleaned text
    return clean[:300] + "..."


def formulate_vertex_search_query(
    query: str = "",
    ticker: Optional[str] = None,
    requested_years: Optional[List[int]] = None,
    fiscal_year: Optional[int] = None,
    keyword: Optional[str] = None,
) -> str:
    """Formulates an optimized hybrid search query string combining metadata anchor terms and semantic intent."""
    terms = []
    if ticker:
        terms.append(ticker.upper())

    target_years = requested_years if requested_years else ([fiscal_year] if fiscal_year else None)
    if target_years:
        terms.extend([str(y) for y in target_years])

    clean_query = ""
    if query:
        # Strip conversational preamble noise (e.g. "Can you please explain to me what...", "Please show me...")
        clean_query = re.sub(
            r'^(?:can you|please|could you|explain|tell me|show me|what are|what is|how did|describe|to me|\s+)+',
            '',
            query.strip(),
            flags=re.IGNORECASE,
        ).strip()

    if clean_query:
        terms.append(clean_query)
    elif keyword:
        terms.append(keyword)

    return " ".join(terms) if terms else "SEC 10-K filings"


class SECDocumentChunk(BaseModel):
    """Chunk of SEC 10-K filing text with GCS grounding metadata."""

    chunk_id: str
    ticker: str
    company_name: str
    fiscal_year: int
    section: str = "Item 7 - MD&A"  # "Item 7 - MD&A" or "Item 1A - Risk Factors"
    content: str
    highlight_excerpt: str = ""
    citation: str
    gcs_uri: str
    keywords: List[str] = Field(default_factory=list)


def clean_sec_document_text(raw_text: str) -> str:
    """Strips redundant header preambles, section banners, URLs, and HTML entities while preserving Markdown formatting & tables."""
    if not raw_text:
        return ""

    # If raw_text contains HTML tags, run SEC10KHTMLToMarkdownParser first
    if "<table" in raw_text.lower() or "<div" in raw_text.lower() or "<p>" in raw_text.lower():
        from scripts.fetch_real_unabridged_sec_filings import SEC10KHTMLToMarkdownParser
        parser = SEC10KHTMLToMarkdownParser()
        parser.feed(raw_text)
        text = parser.get_markdown()
    else:
        text = raw_text

    # 1. Comprehensive HTML entity decoding
    text = re.sub(r'&\#8212;', ' — ', text)
    text = re.sub(r'&\#8211;', ' – ', text)
    text = re.sub(r'&\#8220;', '"', text)
    text = re.sub(r'&\#8221;', '"', text)
    text = re.sub(r'&\#8217;', "'", text)
    text = re.sub(r'&\#8226;', ' • ', text)
    text = re.sub(r'&\#8230;', '...', text)
    text = re.sub(r'&\#160;|&nbsp;', ' ', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#39;', "'", text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&\#\d+;', ' ', text)
    text = re.sub(r'&amp;', '&', text)

    # 2. Strip dataset header preambles and URLs
    text = re.sub(r'#+\s*REAL UNABRIDGED SEC EDGAR FILING:[^#\n]*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*Source URL:\s*https?://[^\s]*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'#+\s*Section:\s*Item[^\n]*?\n?', '', text, flags=re.IGNORECASE)

    # 3. Structure ITEM section titles into Markdown headings
    text = re.sub(r'\bITEM\s+7\.\s+MANAGEMENT\'S\s+DISCUSSION\s+AND\s+ANALYSIS[^\n.]*', '# Item 7. Management\'s Discussion and Analysis (MD&A)', text, flags=re.IGNORECASE)
    text = re.sub(r'\bITEM\s+1A\.\s+RISK\s+FACTORS', '# Item 1A. Risk Factors', text, flags=re.IGNORECASE)

    # 4. Standardize list bullet markers (e.g. •, ·, (a), (b), (i), (ii)) into Markdown list items
    text = re.sub(r'(?:^|\n|\s)\((?:[a-z]|\d{1,2}|i|ii|iii|iv|v)\)\s+', '\n- ', text)
    text = re.sub(r'(?:^|\n|\s)[•·]\s*', '\n- ', text)

    # 5. Generic paragraph boundary separation (excluding Markdown table lines starting with '|')
    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        if line.strip().startswith('|'):
            processed_lines.append(line)
        else:
            line_clean = re.sub(r'(?<!\bItem 1A)(?<!\bItem 1B)(?<!\bItem 7)(?<!\bItem 7A)(?<!\bInc)(?<!\bCorp)(?<!\bU\.S)(?<!\bFY\d\d)(?<!\bNo)(?<!\b\d[A-Z])([.!?])\s+([A-Z][a-z]{2,})', r'\1\n\n\2', line)
            processed_lines.append(line_clean)
    text = '\n'.join(processed_lines)

    # 6. Fix Mojibake encoding artifacts (â€™, â€œ, â€¢, â„¢) & normalize quotes
    from scripts.fetch_real_unabridged_sec_filings import fix_sec_mojibake_encoding
    text = fix_sec_mojibake_encoding(text)
    return text.strip()


class SECCorpusStore:
    """Document corpus store managing SEC 10-K disclosures grounded exclusively in GCP Vertex AI Search."""

    def __init__(self):
        self.vertex_search = VertexAISearchClient(datastore_id="sec-10k-filings-datastore")

    def search_chunks(
        self,
        query_str: str = "",
        ticker: Optional[str] = None,
        requested_years: Optional[List[int]] = None,
        fiscal_year: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> List[SECDocumentChunk]:
        """Searches document corpus chunks strictly via Vertex AI Search DataStore using formulated hybrid queries."""
        search_query = formulate_vertex_search_query(
            query=query_str,
            ticker=ticker,
            requested_years=requested_years,
            fiscal_year=fiscal_year,
            keyword=keyword,
        )

        vertex_results = self.vertex_search.search_filings(search_query, page_size=5)
        v_chunks = []
        target_years = requested_years if requested_years else ([fiscal_year] if fiscal_year else None)
        for vr in vertex_results:
            uri_match = re.search(r'/([A-Z0-9]+)_(\d{4})_', vr.gcs_uri)
            extracted_ticker = ticker or (uri_match.group(1) if uri_match else "SEC")
            extracted_year = (int(uri_match.group(2)) if uri_match else None) or (target_years[0] if (target_years and len(target_years) > 0) else 2024)

            doc_meta_lower = (vr.gcs_uri + " " + vr.title).lower()
            if "item1a" in doc_meta_lower or "item 1a" in doc_meta_lower or "item1a_risk" in doc_meta_lower:
                sec_section = "Item 1A - Risk Factors"
            elif "item7" in doc_meta_lower or "item 7" in doc_meta_lower or "item7_mda" in doc_meta_lower:
                sec_section = "Item 7 - MD&A"
            elif "risk" in doc_meta_lower:
                sec_section = "Item 1A - Risk Factors"
            else:
                sec_section = "Item 7 - MD&A"

            cleaned_content = clean_sec_document_text(vr.snippet)
            excerpt = extract_relevant_excerpt(cleaned_content, query_str)

            v_chunks.append(
                SECDocumentChunk(
                    chunk_id=vr.id,
                    ticker=extracted_ticker,
                    company_name=f"{extracted_ticker} Corp",
                    fiscal_year=extracted_year,
                    section=sec_section,
                    content=cleaned_content,
                    highlight_excerpt=excerpt,
                    citation=f"Vertex AI Search ({self.vertex_search.datastore_id}) [{vr.gcs_uri}]",
                    gcs_uri=vr.gcs_uri,
                )
            )
        return v_chunks


def search_sec_filing_chunks_tool(
    query: str = "",
    ticker: str = "",
    requested_years: List[int] = [],
) -> list:
    """Searches unstructured SEC 10-K filing disclosures (MD&A and Risk Factors) grounded in GCS using Vertex AI Search.

    Args:
        query: Topic, keywords, or natural language query (e.g., 'Tesla business risks', 'Nvidia AI R&D spend').
        ticker: Target ticker symbol (e.g. AAPL, MSFT, NVDA, TSLA).
        requested_years: List of target fiscal years (e.g., [2023] or [2022, 2023, 2024]).
    """
    store = SECCorpusStore()

    chunks = store.search_chunks(
        query_str=query,
        ticker=ticker or None,
        requested_years=requested_years or None,
    )
    dumped = [c.model_dump() for c in chunks]
    add_grounded_chunks(dumped)
    return dumped
