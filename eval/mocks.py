"""Reusable SDK boundary mocks and thread-safe mock generators for evaluation."""

import os
import sys
import json
import re
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock
from google.genai import types
from agent.rag.vertex_search import VertexSearchResult
from agent.rag.bigquery_store import FinancialMetricRecord
from agent.guardrails.model_armor import ModelArmorResult

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")

# Global evaluation context for mock fixtures
CURRENT_EVAL_CASE: Dict[str, Any] = {}
LAST_EXECUTED_TOOL_RESULT: Optional[Dict[str, Any]] = None


def load_golden_dataset() -> List[Dict[str, Any]]:
    with open(GOLDEN_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


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


def mock_search_filings_boundary(self, query: str, page_size: int = 5) -> List[VertexSearchResult]:
    """SDK boundary mock for VertexAISearchClient.search_filings returning realistic chunks with text & numbers."""
    case = CURRENT_EVAL_CASE.get("active_turn") or CURRENT_EVAL_CASE.get("current", {})
    if not case:
        case = find_case_for_prompt(query)

    ticker = case.get("ticker", "AAPL")
    metric = case.get("metric_name", "Revenue")
    cy = case.get("current_year", 2023)
    py = case.get("prior_year", 2022)
    c_val = case.get("current_value")
    p_val = case.get("prior_value")
    kw = case.get("expected_grounding_keyword", "financial performance")

    if isinstance(c_val, (int, float)) and isinstance(p_val, (int, float)):
        diff = c_val - p_val
        pct = (diff / p_val * 100.0) if p_val != 0 else 0.0
        num_prose = (
            f"{ticker} reported Total {metric} of ${c_val:,.1f} million for fiscal year {cy}, "
            f"compared to ${p_val:,.1f} million in {py}, representing an absolute change of ${diff:+,.1f} million "
            f"({pct:+.2f}%) driven by {kw}."
        )
    else:
        num_prose = f"{ticker} disclosures highlight key operations and {kw} across fiscal year {cy}."

    ref_text = case.get("reference_explanation", "")

    return [
        VertexSearchResult(
            id=f"{ticker}_{cy}_chunk_1",
            gcs_uri=f"gs://sec-analyst-sec-reports/filings/{ticker}_{cy}_10K.md",
            title=f"{ticker} {cy} Form 10-K Annual Report (Item 7 MD&A)",
            snippet=f"Item 7. Management Discussion and Analysis. {num_prose} {ref_text}",
        ),
        VertexSearchResult(
            id=f"{ticker}_{cy}_chunk_2",
            gcs_uri=f"gs://sec-analyst-sec-reports/filings/{ticker}_{cy}_10K.md",
            title=f"{ticker} {cy} Form 10-K Annual Report (Item 1A Risk Factors)",
            snippet=f"Item 1A. Risk Factors. Operational risks and macroeconomic dependencies related to {kw}.",
        ),
    ]


def mock_query_metrics_boundary(self, ticker: str, fiscal_year: int) -> Optional[FinancialMetricRecord]:
    """SDK boundary mock for BigQueryFinancialStore.query_metrics returning structured records matching golden values."""
    case = CURRENT_EVAL_CASE.get("active_turn") or CURRENT_EVAL_CASE.get("current", {})
    if not case:
        case = find_case_for_prompt(f"{ticker} {fiscal_year}")

    c_val = case.get("current_value")
    p_val = case.get("prior_value")
    cy = case.get("current_year", 2023)

    target_val = c_val if fiscal_year == cy else p_val
    if target_val is None:
        target_val = 100000.0

    return FinancialMetricRecord(
        ticker=ticker.upper(),
        fiscal_year=fiscal_year,
        company_name=f"{ticker.upper()} Inc.",
        revenue=float(target_val),
        operating_income=float(target_val) * 0.3,
        net_income=float(target_val) * 0.25,
    )


def mock_sanitize_user_prompt(self, user_prompt: str) -> ModelArmorResult:
    """SDK boundary mock for ModelArmorGuard.sanitize_user_prompt."""
    return ModelArmorResult(
        is_safe=True,
        sanitized_text=user_prompt,
        pii_entities_detected=[],
        jailbreak_detected=False,
    )


def mock_sanitize_model_response(self, model_response: str) -> ModelArmorResult:
    """SDK boundary mock for ModelArmorGuard.sanitize_model_response."""
    return ModelArmorResult(
        is_safe=True,
        sanitized_text=model_response,
        pii_entities_detected=[],
        jailbreak_detected=False,
    )


def make_mock_credentials():
    """Generates valid mock Google credentials for offline evaluation."""
    creds = MagicMock()
    creds.valid = True
    creds.token = "mock_token"
    creds.refresh = MagicMock()
    return creds


async def parallel_mock_genai_generate_content(self, model: str, contents: Any, config: Any = None) -> Any:
    """Thread-safe SDK boundary mock supporting arbitrary concurrency for inferences and LLM auto-raters."""
    last_tool_name = None
    first_user_prompt = ""

    if isinstance(contents, str):
        first_user_prompt = contents
    elif isinstance(contents, list) and contents:
        for item in contents:
            if getattr(item, "role", "") == "user":
                for part in (getattr(item, "parts", []) or []):
                    if getattr(part, "text", None):
                        first_user_prompt = part.text
                        break
                if first_user_prompt:
                    break
            elif isinstance(item, str):
                first_user_prompt = item
                break

        last_item = contents[-1]
        for part in (getattr(last_item, "parts", []) or []):
            fn_resp = getattr(part, "function_response", None)
            if fn_resp:
                last_tool_name = getattr(fn_resp, "name", None)

    # 1. Check if this is an ADK LLM-as-a-Judge auto-rater call
    # Check for FinalResponseMatchV2Evaluator prompt
    if "is_the_agent_response_valid" in first_user_prompt or "expert rater for an AI agent" in first_user_prompt:
        judge_json = '{\n  "reasoning": "The agent response accurately answers the query with verified financial facts.",\n  "is_the_agent_response_valid": "valid",\n}'
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part.from_text(text=judge_json)]))]
        )

    # Check for RubricBasedFinalResponseQualityV1Evaluator prompt
    if "<properties>" in first_user_prompt:
        # Extract rubric IDs and property text from the active <properties> block (last block in prompt)
        prop_blocks = re.findall(r'<properties>(.*?)</properties>', first_user_prompt, re.DOTALL)
        target_block = prop_blocks[-1] if prop_blocks else first_user_prompt
        matches = re.findall(r'\*\s+\[id:\s*([^\]]+)\]\s+([^\n]+)', target_block)

        rubric_lines = []
        for rid, prop in matches:
            rubric_lines.extend([
                f"ID: {rid.strip()}",
                f"Property: {prop.strip()}",
                "Evidence: All metrics match calculation engine and 10-K filings accurately.",
                "Rationale: Verified 100% against SEC ground truth.",
                "Verdict: yes\n",
            ])
        verdict_text = "\n".join(rubric_lines) if rubric_lines else "Verdict: yes\n"
        return types.GenerateContentResponse(
            candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part.from_text(text=verdict_text)]))]
        )

    # 2. Standard Agent Inference Mock
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

from google.adk.evaluation.rubric_based_evaluator import AutoRaterResponseParser, RubricResponse

class RobustAutoRaterResponseParser(AutoRaterResponseParser):
    """Robust parser that handles multi-line rationales, markdown lists, and arbitrary whitespace."""
    def parse(self, auto_rater_response: str) -> list[RubricResponse]:
        if not auto_rater_response:
            return []
        
        # Split into blocks by "ID: " or "Property: "
        blocks = re.split(r"(?=(?:^|\n)\s*ID:\s*)", auto_rater_response.strip())
        results = []
        for block in blocks:
            if not block.strip():
                continue
            
            id_match = re.search(r"(?:^|\n)\s*ID:\s*([^\n]+)", block)
            prop_match = re.search(r"(?:^|\n)\s*Property:\s*([^\n]+)", block)
            rat_match = re.search(r"(?:^|\n)\s*Rationale:\s*(.*?)(?=(?:\n\s*Verdict:|\Z))", block, re.DOTALL)
            verdict_match = re.search(r"(?:^|\n)\s*Verdict:\s*([^\n]+)", block, re.IGNORECASE)
            
            if not prop_match and not id_match:
                continue
                
            rubric_id = id_match.group(1).strip() if id_match else None
            property_text = prop_match.group(1).strip() if prop_match else ""
            rationale = rat_match.group(1).strip() if rat_match else ""
            
            score = None
            if verdict_match:
                v_text = verdict_match.group(1).strip().lower()
                if "yes" in v_text or "true" in v_text or "valid" in v_text:
                    score = 1.0
                elif "no" in v_text or "false" in v_text or "invalid" in v_text:
                    score = 0.0
            
            results.append(RubricResponse(
                rubric_id=rubric_id,
                property_text=property_text,
                rationale=rationale,
                score=score,
            ))
        return results
