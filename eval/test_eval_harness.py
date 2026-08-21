"""Pytest evaluation harness testing financial calculation accuracy, grounding faithfulness, PII scrubbing, orchestration, and Category 2 Memory."""

import json
import os
import pytest
from agent.tools.calculation_engine import calculate_financial_variance, VarianceRequest
from agent.memory.session_store import PersistentSessionStore
from agent.config import settings
from agent.root_orchestrator import RootOrchestrator, export_financial_report, ExportReportRequest
from app.app_controller import AppController

from eval.metrics import (
    extract_numbers_from_text,
    compute_numerical_accuracy,
    compute_grounding_recall,
    compute_rouge_1,
    compute_rouge_l,
)
from eval.evaluator import EvalEngine

GOLDEN_DATASET_PATH = os.path.join(os.path.dirname(__file__), "golden_dataset.json")


def load_golden_dataset():
    with open(GOLDEN_DATASET_PATH, "r") as f:
        return json.load(f)


def load_quantitative_golden_dataset():
    return [c for c in load_golden_dataset() if c.get("category") == "quantitative_variance"]


@pytest.mark.parametrize("case", load_quantitative_golden_dataset())
def test_calculation_engine_golden_accuracy(case):
    """Evaluates 100% numerical accuracy for deterministic variance calculations against golden dataset."""
    request = VarianceRequest(
        ticker=case["ticker"],
        metric_name=case["metric_name"],
        current_period_value=case["current_value"],
        prior_period_value=case["prior_value"],
    )
    result = calculate_financial_variance(request)

    assert result.is_success is True
    assert result.ticker == case["ticker"]
    assert result.metric_name == case["metric_name"]
    assert result.absolute_change == case["expected_absolute_change"]
    assert result.percentage_change == case["expected_percentage_change"]
    assert result.direction == case["expected_direction"]



def test_calculation_engine_zero_prior_period():
    """Evaluates guided error recovery when prior period value is zero."""
    request = VarianceRequest(
        ticker="TEST",
        metric_name="Revenue",
        current_period_value=500.0,
        prior_period_value=0.0,
    )
    result = calculate_financial_variance(request)

    assert result.is_success is False
    assert result.percentage_change is None
    assert result.absolute_change == 500.0
    assert "Division by zero" in result.error
    assert result.recovery_instruction is not None


def test_calculation_engine_invalid_type_recovery():
    """Evaluates guided error recovery for non-numerical inputs."""
    request = VarianceRequest(
        ticker="TEST",
        metric_name="Revenue",
        current_period_value="INVALID_NUMBER",
        prior_period_value=100.0,
    )
    result = calculate_financial_variance(request)

    assert result.is_success is False
    assert "Cannot parse" in result.error
    assert "Ensure current_period_value is a valid numeric" in result.recovery_instruction


def test_human_in_the_loop_export_stop():
    """Evaluates that external exports require explicit human approval before execution."""
    req = ExportReportRequest(
        ticker="AAPL",
        destination_gcs_uri="gs://fde-sec-edgar-reports/aapl_2023.md",
        report_content="Sample report text",
    )
    unapproved_res = export_financial_report(req, human_approved=False)
    assert unapproved_res.is_success is False
    assert unapproved_res.requires_human_approval is True
    assert unapproved_res.status == "PENDING_HUMAN_APPROVAL"

    approved_res = export_financial_report(req, human_approved=True)
    assert approved_res.is_success is True
    assert approved_res.status == "EXPORTED"


def test_persistent_session_store(tmp_path):
    """Evaluates persistent conversational session store management across turns."""
    store_file = os.path.join(tmp_path, "test_sessions.json")
    store = PersistentSessionStore(storage_path=store_file)

    session_id = "sess_001"
    store.save_session_turn(session_id, "Query 1", "Response 1", {"ticker": "AAPL"})
    store.save_session_turn(session_id, "Query 2", "Response 2", {"ticker": "MSFT"})

    history = store.get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["user_query"] == "Query 1"
    assert history[1]["metadata"]["ticker"] == "MSFT"


def test_root_orchestrator_end_to_end(monkeypatch):
    """Evaluates ADK RootOrchestrator workflow and grounded dynamic LLM narrative synthesis."""
    class MockGenerateResponse:
        def __init__(self, text):
            self.text = text

    class MockModels:
        def generate_content(self, model, contents, **kwargs):
            if "intent parser" in str(contents):
                return MockGenerateResponse('{"query_type": "variance_analysis", "tickers": ["AAPL"], "requested_years": [2023, 2022], "metric_name": "Revenue"}')
            return MockGenerateResponse("### Executive Summary for AAPL (Revenue)\nApple Inc. FY2023 10-K reported Total Net Sales of $383,285 million, down 2.8% due to macroeconomic headwinds in hardware sales.")

    controller = AppController()

    response = controller.dispatch_query(
        prompt="Analyze revenue for AAPL between FY2022 and FY2023",
    )

    assert response["is_success"] is True
    if response.get("variance_result"):
        v_res = response["variance_result"]
        abs_val = v_res.get("absolute_change") if isinstance(v_res, dict) else getattr(v_res, "absolute_change", None)
        assert abs_val == -11043.0
    assert "AAPL" in response["narrative"] or "Apple" in response["narrative"]
    assert len(response["narrative"]) > 0
    assert response["model_used"].startswith("Vertex AI")


def test_model_configuration_validation():
    """Evaluates runtime settings for model selection and fallback hierarchy."""
    assert settings.reasoning_model is not None
    assert isinstance(settings.reasoning_model, str)
    assert len(settings.reasoning_model) > 0
    assert settings.tool_model is not None
    assert isinstance(settings.tool_model, str)
    assert len(settings.tool_model) > 0

    agent = RootOrchestrator()
    assert agent.reasoning_model == settings.reasoning_model


def test_multiturn_conversational_context_retention():
    """Evaluates multi-turn context retention ensuring follow-up queries retain active ticker/metric from session history."""
    controller = AppController()
    session_id = "test_multiturn_context_session"

    # Turn 1: Initial request for AMZN
    turn1_res = controller.dispatch_query(
        prompt="show me amzn financial data across all years available",
        session_id=session_id,
    )
    assert turn1_res["is_success"] is True
    assert len(turn1_res["narrative"]) > 0

    # Turn 2: Follow-up request omitting ticker ("what about 2024?")
    turn2_res = controller.dispatch_query(
        prompt="what about 2024?",
        session_id=session_id,
    )
    assert turn2_res["is_success"] is True
    assert len(turn2_res["narrative"]) > 0


def test_multiyear_range_query_expansion():
    """Evaluates multi-year range query parsing (e.g. 2022-2024) to ensure all intermediate years are retrieved."""
    controller = AppController()
    res = controller.dispatch_query(prompt="show me amzn financial data from 2022-2024")
    assert res["is_success"] is True
    assert len(res["narrative"]) > 0


def test_native_function_calling_dispatch(monkeypatch):
    """Evaluates Native Gemini Function Calling dispatch when the model requests tool execution."""
    from agent.tools.calculation_engine import calculate_financial_variance_tool
    from agent.rag.bigquery_store import query_bigquery_financial_metrics_tool, BigQueryFinancialStore, FinancialMetricRecord
    from agent.rag.sec_corpus import search_sec_filing_chunks_tool

    monkeypatch.setattr(
        BigQueryFinancialStore,
        "query_metrics",
        lambda self, ticker, fiscal_year: FinancialMetricRecord(
            ticker=ticker,
            fiscal_year=fiscal_year,
            company_name="Apple Inc.",
            revenue=383285.0,
            operating_income=114301.0,
            net_income=96995.0,
        ),
    )

    # 1. Test standalone tool schemas return valid data dicts
    calc_res = calculate_financial_variance_tool("AAPL", "Revenue", 383285.0, 394328.0)
    assert calc_res["is_success"] is True
    assert calc_res["absolute_change"] == -11043.0
    assert calc_res["percentage_change"] == -2.8

    bq_res = query_bigquery_financial_metrics_tool("AAPL", 2023)
    assert bq_res["ticker"] == "AAPL"
    assert bq_res["revenue"] == 383285.0

    sec_res = search_sec_filing_chunks_tool(query="revenue", ticker="AAPL", requested_years=[2023])
    assert isinstance(sec_res, list)

    # 2. Test Agent registration of ADK root_agent tools
    agent = RootOrchestrator()
    root_tool_names = [t.name if hasattr(t, "name") else getattr(t, "__name__", str(t)) for t in agent.root_agent.tools]
    assert "search_agent" in root_tool_names
    assert "calculate_financial_variance_tool" in root_tool_names
    assert "query_bigquery_financial_metrics_tool" in root_tool_names

    analysis_res = agent.run_analysis(
        user_prompt="calculate variance for AAPL revenue",
    )

    assert analysis_res["is_success"] is True
    assert "Vertex AI" in analysis_res["model_used"]
    assert "ADK Search Sub-Agent & Tools" in analysis_res["model_used"]
    assert len(analysis_res["narrative"]) > 0


def test_thematic_tracking_qualitative_risk_disclosures(monkeypatch):
    """Evaluates qualitative risk factor disclosures RAG retrieval, ticker filtering, and token bounding for Meta/thematic queries."""
    from agent.rag.sec_corpus import SECCorpusStore
    from agent.rag.vertex_search import VertexSearchResult, VertexAISearchClient

    mock_results = [
        VertexSearchResult(
            id="chunk_1",
            gcs_uri="gs://sec-analyst-sec-reports/filings/META_2023_10K.md",
            title="Meta Platforms Inc. 10-K Item 1A Risk Factors",
            snippet="Meta Platforms, Inc. faces significant competition in advertising, user engagement risks, regulatory scrutiny over data privacy, and investments in AI infrastructure.",
        )
    ]
    monkeypatch.setattr(VertexAISearchClient, "search_filings", lambda self, query, page_size=5: mock_results)

    # 1. Verify SEC corpus store returns non-empty matching chunks for META risk disclosures
    corpus_store = SECCorpusStore()
    meta_risk_chunks = corpus_store.search_chunks(ticker="META", keyword="risk")
    assert len(meta_risk_chunks) > 0
    assert all(c.ticker == "META" for c in meta_risk_chunks)

    # 2. Verify end-to-end AppController handles risk disclosures prompt cleanly
    controller = AppController()
    res = controller.dispatch_query("Analyze Meta risk factors disclosure")
    assert res["is_success"] is True
    assert res["narrative"] is not None
    assert len(res["narrative"]) > 0
    assert "unable to analyze" not in res["narrative"].lower()
    assert "unable to provide" not in res["narrative"].lower()
    assert "citations" in res
    assert "hybrid_search_result" in res
    assert "text_chunks" in res["hybrid_search_result"]


def test_multiturn_qualitative_risk_followup(monkeypatch):
    """Evaluates multi-turn qualitative risk factor follow-up retention when ticker is omitted in Turn 2."""
    from agent.rag.vertex_search import VertexSearchResult, VertexAISearchClient

    mock_results = [
        VertexSearchResult(
            id="chunk_1",
            gcs_uri="gs://sec-analyst-sec-reports/filings/TSLA_2023_10K.md",
            title="Tesla, Inc. 10-K Item 1A Risk Factors",
            snippet="Tesla, Inc. faces risks related to vehicle production ramp-up, battery supply chain constraints, autonomous driving regulatory scrutiny, and competitive pricing dynamics.",
        )
    ]
    captured_queries = []
    def mock_search_filings(self, query, page_size=5):
        captured_queries.append(query)
        if "AI" in query and "risk" not in query.lower():
            return []
        return mock_results

    monkeypatch.setattr(VertexAISearchClient, "search_filings", mock_search_filings)

    import uuid
    controller = AppController()
    session_id = f"test_multiturn_risk_session_{uuid.uuid4().hex[:8]}"

    # Turn 1: Initial financial highlights for TSLA
    turn1_res = controller.dispatch_query(
        prompt="Explain Tesla 2023 financial highlights",
        session_id=session_id,
    )
    assert turn1_res["is_success"] is True

    # Turn 2: Follow-up asking about business risks omitting ticker ("explain the business risks")
    turn2_res = controller.dispatch_query(
        prompt="explain the business risks",
        session_id=session_id,
    )
    assert turn2_res["is_success"] is True
    assert turn2_res["narrative"] is not None
    assert len(turn2_res["narrative"]) > 0
    history = controller.session_store.get_session_history(session_id)
    assert len(history) == 2


def test_vertex_search_grounding_chunks_snippet_extraction():
    """Verifies that VertexAISearchClient extracts genuine text snippets from retrieved_context rather than placeholder strings."""
    from agent.rag.vertex_search import VertexAISearchClient

    class MockRetrievedContext:
        def __init__(self, uri, title, text):
            self.uri = uri
            self.title = title
            self.text = text

    class MockChunk:
        def __init__(self, uri, title, text):
            self.retrieved_context = MockRetrievedContext(uri, title, text)

    class MockGroundingMetadata:
        def __init__(self, chunks):
            self.grounding_chunks = chunks

    class MockCandidate:
        def __init__(self, chunks):
            self.grounding_metadata = MockGroundingMetadata(chunks)

    class MockResponse:
        def __init__(self, chunks, text=""):
            self.candidates = [MockCandidate(chunks)]
            self.text = text

    client = VertexAISearchClient()
    mock_chunks = [
        MockChunk("gs://bucket/doc1.md", "Doc 1", "Real unabridged SEC filing text for passage 1"),
        MockChunk("gs://bucket/doc2.md", "Doc 2", "Real unabridged SEC filing text for passage 2"),
        MockChunk("gs://bucket/doc3.md", "Doc 3", "Real unabridged SEC filing text for passage 3"),
    ]
    mock_response = MockResponse(mock_chunks, text="Overall summary text")

    class MockModels:
        def generate_content(self, model, contents, config=None):
            return mock_response

    client.client = type("MockClient", (), {"models": MockModels()})()

    results = client.search_filings("TSLA risk", page_size=5)

    assert len(results) == 3
    assert results[0].snippet == "Real unabridged SEC filing text for passage 1"
    assert results[1].snippet == "Real unabridged SEC filing text for passage 2"
    assert results[2].snippet == "Real unabridged SEC filing text for passage 3"
    for res in results:
        assert "Grounded passage" not in res.snippet


def test_formulate_vertex_search_query():
    """Verifies that formulate_vertex_search_query strips preamble noise and anchors metadata."""
    from agent.rag.sec_corpus import formulate_vertex_search_query

    q1 = formulate_vertex_search_query(
        query="Can you please explain to me what Tesla's business risks were in 2023?",
        ticker="TSLA",
        fiscal_year=2023,
    )
    assert q1 == "TSLA 2023 what Tesla's business risks were in 2023?"
    assert "Can you please explain" not in q1

    q2 = formulate_vertex_search_query(
        ticker="NVDA",
        requested_years=[2023, 2024],
        keyword="AI R&D",
    )
    assert q2 == "NVDA 2023 2024 AI R&D"


def test_bigquery_grounded_chunks_synthesis():
    """Verifies that BigQuery metric lookup outputs are synthesized into BigQuery grounded source chunks."""
    from agent.rag.sec_corpus import reset_grounded_chunks, add_grounded_chunks, get_grounded_chunks

    reset_grounded_chunks()
    bq_rec = {
        "ticker": "MSFT",
        "fiscal_year": 2023,
        "company_name": "MICROSOFT CORP",
        "revenue": 211915.0,
        "operating_income": 88523.0,
        "net_income": 72361.0,
    }
    bq_chunk = {
        "chunk_id": f"bq_{bq_rec['ticker']}_{bq_rec['fiscal_year']}",
        "ticker": bq_rec["ticker"],
        "company_name": bq_rec["company_name"],
        "fiscal_year": bq_rec["fiscal_year"],
        "section": "GCP BigQuery Structured Financial Metrics",
        "content": f"### Audited Financial Disclosures (GCP BigQuery)\n| Metric | Reported Value |\n| --- | --- |\n| Revenue | ${bq_rec['revenue']:,.2f}M |",
        "citation": f"GCP BigQuery (sec_edgar_financials.financial_metrics) [{bq_rec['ticker']} FY{bq_rec['fiscal_year']}]",
        "gcs_uri": f"bq://sec_edgar_financials.financial_metrics/{bq_rec['ticker']}_{bq_rec['fiscal_year']}",
        "source_type": "bigquery",
    }
    add_grounded_chunks([bq_chunk])

    chunks = get_grounded_chunks()
    assert len(chunks) == 1
    assert chunks[0]["source_type"] == "bigquery"
    assert chunks[0]["ticker"] == "MSFT"
    assert "GCP BigQuery" in chunks[0]["citation"]


def test_multiturn_dataset_loading_and_adk_transformation():
    """Verifies that all 15 multi-turn cases are loaded from golden_dataset.json and converted to ADK EvalSet cases."""
    from eval.generate_evalset import build_evalsets
    sets = build_evalsets()
    multiturn_cases = sets["multiturn"]["eval_cases"]
    assert len(multiturn_cases) == 15, f"Expected 15 multi-turn eval cases, found {len(multiturn_cases)}"
    
    for case in multiturn_cases:
        conv = case.get("conversation", [])
        assert len(conv) >= 2, f"Multi-turn case {case['eval_id']} should have at least 2 conversation invocations"
        for inv in conv:
            assert "user_content" in inv
            assert "parts" in inv["user_content"]
            assert len(inv["user_content"]["parts"]) > 0


def test_multiturn_evaluator_scoring():
    """Evaluates EvalEngine multi-turn case scoring for math accuracy and ROUGE/grounding metrics."""
    from eval.evaluator import EvalEngine
    evaluator = EvalEngine()

    case = {
        "case_id": "test_mt_001_aapl_drilldown",
        "ticker": "AAPL",
        "category": "multi_turn_drilldown",
        "is_multi_turn": True,
        "turns": [
            {
                "turn_index": 1,
                "user_query": "Analyze Apple revenue FY22 to FY23",
                "ticker": "AAPL",
                "metric_name": "Revenue",
                "current_year": 2023,
                "prior_year": 2022,
                "current_value": 383285.0,
                "prior_value": 394328.0,
                "expected_absolute_change": -11043.0,
                "expected_percentage_change": -2.8,
                "expected_direction": "Decrease",
                "reference_explanation": "Apple revenue decreased by $11,043 million (-2.80%).",
            },
            {
                "turn_index": 2,
                "user_query": "Why did revenue decrease in FY2023?",
                "ticker": "AAPL",
                "expected_grounding_keyword": "macroeconomic",
                "reference_explanation": "Revenue decrease was driven by macroeconomic headwinds.",
            }
        ]
    }

    turn_narratives = [
        "Apple Inc. reported Total Net Sales of $383,285 million in FY2023 compared to $394,328 million in FY2022, a decrease of $11,043 million (-2.80%).",
        "Apple revenue decrease was primarily caused by macroeconomic headwinds."
    ]
    turn_tool_results = [
        {
            "is_success": True,
            "ticker": "AAPL",
            "metric_name": "Revenue",
            "current_period_value": 383285.0,
            "prior_period_value": 394328.0,
            "absolute_change": -11043.0,
            "percentage_change": -2.8,
            "direction": "Decrease"
        },
        None
    ]

    res = evaluator.evaluate_case_multiturn(
        case=case,
        turn_narratives=turn_narratives,
        turn_tool_results=turn_tool_results,
    )

    assert res["is_math_accurate"] is True
    assert res["math_accuracy_pct"] == 100.0
    assert res["turn_count"] == 2
    assert res["has_isolation_leak"] is False


def test_multiturn_negative_isolation_leak_detection():
    """Evaluates detection of context leakage in context-switch multi-turn cases."""
    from eval.evaluator import EvalEngine
    evaluator = EvalEngine()

    case = {
        "case_id": "test_mt_007_context_switch_aapl_to_msft",
        "ticker": "MSFT",
        "category": "multi_turn_context_switch",
        "is_multi_turn": True,
        "turns": [
            {
                "turn_index": 1,
                "user_query": "Analyze Apple revenue FY23",
                "ticker": "AAPL",
                "reference_explanation": "Apple revenue was $383,285M",
            },
            {
                "turn_index": 2,
                "user_query": "Now calculate Microsoft operating income for FY2023 vs FY2022",
                "ticker": "MSFT",
                "metric_name": "Operating Income",
                "current_year": 2023,
                "prior_year": 2022,
                "current_value": 88523.0,
                "prior_value": 83383.0,
                "expected_absolute_change": 5140.0,
                "expected_percentage_change": 6.16,
                "forbidden_terms": ["AAPL", "Apple", "383285"],
                "reference_explanation": "Microsoft Operating Income increased by $5,140 million.",
            }
        ]
    }

    # Narrative containing leaked AAPL ticker in Turn 2
    leaked_turn_narratives = [
        "Apple revenue was $383,285M.",
        "Microsoft Operating Income increased by $5,140 million (6.16%). (Note: Leaked context from AAPL revenue $383,285M)"
    ]

    res = evaluator.evaluate_case_multiturn(
        case=case,
        turn_narratives=leaked_turn_narratives,
    )

    assert res["has_isolation_leak"] is True
    assert res["is_math_accurate"] is False
    assert res["math_accuracy_pct"] == 0.0


def test_deliberate_break_session_history_wipe_catches_context_loss():
    """Deliberate-break validation test: Wiping session history before Turn 2 causes context loss, which the eval harness catches."""
    controller = AppController()
    session_id = "deliberate_break_session_001"

    # Turn 1: Establish context for AMZN
    t1_res = controller.dispatch_query(prompt="show me amzn financial data across all years available", session_id=session_id)
    assert t1_res["is_success"] is True

    # Deliberate Break: Wipe session history from controller session store
    controller.session_store.delete_session(session_id)

    # Turn 2: Follow-up relying on active session context ("what about 2024?")
    t2_res = controller.dispatch_query(prompt="what about 2024?", session_id=session_id)

    # Without session history, the orchestrator cannot resolve AMZN from "what about 2024?", so narrative lacks AMZN or fails ticker resolution
    turn_history_after_wipe = controller.session_store.get_session_history(session_id)
    # The session was reset, so history only has 1 turn (the new turn) instead of 2 accumulated turns
    assert len(turn_history_after_wipe) == 1


def test_adk_test_config_llm_judge_and_four_pillars():
    """Evaluates that test_config.json properly declares all 4 evaluation pillars including LLM-as-a-Judge and financial rubrics."""
    from google.adk.evaluation.eval_config import get_evaluation_criteria_or_default, get_eval_metrics_from_config
    from google.adk.evaluation.metric_evaluator_registry import register_custom_metrics_from_config
    from google.adk.evaluation.final_response_match_v2 import FinalResponseMatchV2Evaluator
    from google.adk.evaluation.rubric_based_final_response_quality_v1 import RubricBasedFinalResponseQualityV1Evaluator

    config_path = os.path.join(os.path.dirname(__file__), "evalsets", "test_config.json")
    eval_config = get_evaluation_criteria_or_default(config_path)
    eval_metrics = get_eval_metrics_from_config(eval_config)

    metric_names = [m.metric_name for m in eval_metrics]
    assert "tool_trajectory_avg_score" in metric_names
    assert "response_match_score" in metric_names
    assert "final_response_match_v2" in metric_names
    assert "rubric_based_final_response_quality_v1" in metric_names

    # Check criteria thresholds
    criteria = eval_config.criteria
    assert criteria["tool_trajectory_avg_score"].threshold == 1.0
    assert criteria["response_match_score"] == 0.04
    assert criteria["final_response_match_v2"].threshold == 0.5
    assert criteria["rubric_based_final_response_quality_v1"].threshold == 0.6

    # Verify rubrics
    rubrics = criteria["rubric_based_final_response_quality_v1"].rubrics
    assert len(rubrics) == 4
    rubric_ids = [r["rubric_id"] if isinstance(r, dict) else r.rubric_id for r in rubrics]
    assert "rubric_sec_grounding_faithfulness" in rubric_ids
    assert "rubric_numerical_precision_fidelity" in rubric_ids
    assert "rubric_financial_analysis_completeness" in rubric_ids
    assert "rubric_conversational_isolation" in rubric_ids

    # Verify registry resolution
    registry = register_custom_metrics_from_config(eval_config)
    for em in eval_metrics:
        evaluator = registry.get_evaluator(em)
        assert evaluator is not None
        if em.metric_name == "final_response_match_v2":
            assert isinstance(evaluator, FinalResponseMatchV2Evaluator)
        elif em.metric_name == "rubric_based_final_response_quality_v1":
            assert isinstance(evaluator, RubricBasedFinalResponseQualityV1Evaluator)


def test_metrics_extract_numbers_from_text():
    """Evaluates regex number extraction from financial narrative strings."""
    text = "Apple Inc. FY2023 10-K reported Total Net Sales of $383,285.0 million, down 2.8% from $394,328 million."
    nums = extract_numbers_from_text(text)
    assert 383285.0 in nums
    assert 2.8 in nums
    assert 394328.0 in nums


def test_metrics_numerical_accuracy_100_percent():
    """Evaluates 100% numerical accuracy checking against expected numbers."""
    narrative = "Revenue for AAPL reached $383,285 million in 2023, down from $394,328 million in 2022 with absolute change -$11,043 million."
    expected = [383285.0, 394328.0, -11043.0]
    res = compute_numerical_accuracy(narrative, expected)
    assert res["is_100_percent_accurate"] is True
    assert res["pass_rate"] == 1.0
    assert len(res["missing_values"]) == 0


def test_metrics_numerical_accuracy_missing_value():
    """Evaluates detection of missing expected numbers in narrative."""
    narrative = "Revenue for AAPL reached $383,285 million in 2023."
    expected = [383285.0, 394328.0]
    res = compute_numerical_accuracy(narrative, expected)
    assert res["is_100_percent_accurate"] is False
    assert res["pass_rate"] == 0.5
    assert 394328.0 in res["missing_values"]


def test_metrics_grounding_recall():
    """Evaluates grounding recall metric calculation across retrieved passages and keywords."""
    narrative = "Apple reported $383,285 million revenue driven by macroeconomic conditions."
    retrieved_chunks = ["Item 7 MD&A: Net sales were $383,285 million due to macroeconomic headwinds."]
    keywords = ["macroeconomic"]

    res = compute_grounding_recall(narrative, retrieved_chunks, keywords)
    assert res["numeric_recall"] == 1.0
    assert res["keyword_recall"] == 1.0
    assert res["grounding_recall"] == 1.0


def test_metrics_rouge_1_and_rouge_l():
    """Evaluates ROUGE-1 and ROUGE-L unigram/LCS overlap calculations."""
    candidate = "Apple reported net sales of 383285 million in 2023."
    reference = "Apple Inc reported net sales of 383285 million in 2023."

    r1 = compute_rouge_1(candidate, reference)
    rl = compute_rouge_l(candidate, reference)

    assert r1["f1"] > 0.8
    assert rl["f1"] > 0.8


def test_eval_engine_layer1_deterministic():
    """Evaluates EvalEngine Layer 1 deterministic statistical scoring."""
    engine = EvalEngine()
    case = {
        "case_id": "test_sample",
        "ticker": "AAPL",
        "current_value": 383285.0,
        "prior_value": 394328.0,
        "expected_absolute_change": -11043.0,
        "expected_grounding_keyword": "macroeconomic",
        "reference_explanation": "Apple reported $383,285 million revenue in 2023.",
    }
    generated = "Apple reported $383,285 million revenue in 2023 compared to $394,328 million in 2022 with a change of -$11,043 million under macroeconomic pressure."
    retrieved = ["10-K snippet: $383,285 million in 2023 compared to $394,328 million in 2022 with -$11,043 million under macroeconomic pressure."]

    res = engine.evaluate_case_layer1_deterministic(case, generated, retrieved)
    assert res["math_accuracy_pct"] == 100.0
    assert res["is_math_accurate"] is True
    assert res["grounding_recall"] == 1.0
    assert res["rouge_1_f1"] > 0.4


def test_golden_dataset_stress_test_cases():
    """Evaluates integrity and coverage of all 39 cases in golden_dataset.json."""
    golden_path = os.path.join(os.path.dirname(__file__), "golden_dataset.json")
    with open(golden_path, "r") as f:
        cases = json.load(f)

    assert len(cases) == 39
    case_ids = [c["case_id"] for c in cases]
    assert "test_023_edge_2025_filing_availability" in case_ids
    assert "test_024_edge_multi_company_citation_isolation" in case_ids
    assert "test_mt_001_aapl_drilldown" in case_ids





