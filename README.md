# SEC EDGAR Natural Language Analyst (FDE Capstone Project)

An enterprise-grade, agentic financial analysis platform built on the **Google Agent Development Kit (ADK)** and **Vertex AI**. It automates period-over-period financial variance analysis (Revenue, Operating Income, Net Income), performs longitudinal thematic tracking across SEC 10-K filings, and renders interactive **A2UI** financial visualization surfaces with grounded citations.

---

## 🏛️ Architecture & System Capabilities

- **Orchestration**: Google Agent Development Kit (ADK) `RootOrchestrator` (`agent/root_orchestrator.py`) supervised by `AppController` (`app/app_controller.py`).
- **Hybrid RAG**:
  - **Structured Datastore**: Live GCP BigQuery (`sec_edgar_financials.financial_metrics`) for verified financial facts.
  - **Unstructured SEC Datastore**: Vertex AI Search over official SEC 10-K filings (Item 7 MD&A and Item 1A Risk Factors) with 100% grounded citations.
- **Deterministic Math Engine**: Native calculation engine (`agent/tools/calculation_engine.py`) enforcing mathematical rigor and zero calculation hallucinations.
- **Generative UI (A2UI)**: Native synthesis of interactive JSON-based UI components (charts, summary cards, financial tables) rendered in frontend split-pane view.
- **Enterprise Guardrails**: Pre- and post-execution security with **Model Armor** for PII redaction, prompt injection defense, and Human-In-The-Loop (HITL) approval for GCS report exports.
- **Observability**: OpenTelemetry / Cloud Trace integration with structured JSON audit logging and BigQuery telemetry sink.

---

## 📁 Repository Structure

```
.
├── README.md
├── SPECIFICATION.md
├── AGENTS.md
├── Makefile
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   └── app_controller.py            <- Web & Session Dispatch Controller
├── agent/
│   ├── __init__.py
│   ├── api.py                       <- FastAPI REST API & Web Server
│   ├── cli.py                       <- Interactive Command-Line Interface
│   ├── config.py                    <- Pydantic Settings & Environment Config
│   ├── constitution.py              <- System Constitution & Tool Calling Directives
│   ├── root_orchestrator.py         <- ADK Root Orchestrator (LlmAgent & Runner)
│   ├── guardrails/
│   │   └── model_armor.py           <- Model Armor PII & Injection Filters
│   ├── memory/
│   │   └── session_store.py         <- Persistent Multi-Turn Conversation Store
│   ├── observability/
│   │   ├── logging_config.py        <- Structured JSON Logging
│   │   ├── telemetry_sink.py        <- BigQuery Telemetry Sink
│   │   └── tracer.py                <- OpenTelemetry Tracing
│   ├── rag/
│   │   ├── bigquery_store.py        <- BigQuery Financial Metrics Client
│   │   ├── vertex_search.py         <- Vertex AI Search Client
│   │   └── context_caching.py       <- Gemini Context Cache Manager
│   ├── static/                      <- Interactive Web App Frontend
│   ├── subagents/
│   │   └── search_subagent.py       <- SEC 10-K Search Sub-Agent
│   └── tools/
│       └── calculation_engine.py    <- Deterministic Variance Calculation Engine
├── eval/
│   ├── golden_dataset.json          <- Audited Ground-Truth Evaluation Dataset
│   ├── generate_evalset.py          <- ADK EvalSet Compiler
│   ├── run_adk_eval_parallel.py     <- Parallel ADK Evaluation Runner
│   ├── test_eval_harness.py         <- Core Unit & Integration Pytest Suite
│   ├── test_model_armor.py          <- Security Guardrail Tests
│   ├── test_multi_thread_session.py <- Multi-Turn Session State Tests
│   ├── test_sec_corpus_rag.py       <- RAG Grounding & Citation Tests
│   ├── test_telemetry_sink.py       <- Observability Sink Tests
│   ├── evaluator.py                 <- Dual-Layer Eval Engine (Metrics & Scoring)
│   ├── metrics.py                   <- Deterministic Math, Recall & ROUGE Metrics
│   ├── mocks.py                     <- Thread-Safe SDK & Boundary Mocks
│   └── evalsets/
│       ├── test_config.json         <- ADK 4-Pillar Evaluation Configuration
│       ├── sec_edgar_analyst_master.evalset.json
│       ├── multiturn_revenue_variance.evalset.json
│       └── capstone_demo.evalset.json
└── scripts/
    ├── audit_bigquery_against_sec.py  <- SEC EDGAR XBRL Data Auditor
    └── sync_bigquery_from_sec_edgar.py <- BigQuery Synchronization Tool
```

---

## ⚡ Quick Start & Setup

### 1. Prerequisites
- **Python 3.12+**
- **Google Cloud SDK (`gcloud`)** installed and authenticated:
  ```bash
  gcloud auth application-default login
  ```
- Access to GCP Project with Vertex AI and BigQuery APIs enabled.

### 2. Environment Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Ensure your `.env` contains:
```ini
GCP_PROJECT_ID=sec-analyst
GCP_REGION=us-central1
BIGQUERY_DATASET=sec_edgar_financials
BIGQUERY_TABLE=financial_metrics
VERTEX_SEARCH_DATASTORE_ID=sec-10k-filings-datastore
ORCHESTRATOR_MODEL=gemini-2.5-pro
SEARCH_MODEL=gemini-2.5-pro
```

### 3. Installation
Activate your virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 Running the Application & Agent

### Option A: Web Application & Interactive UI (FastAPI)
Launch the FastAPI server (serves both REST endpoints and the split-pane web UI):
```bash
PYTHONPATH=. uvicorn agent.api:app --host 0.0.0.0 --port 8080 --reload
```
- **Web UI**: Navigate to `http://localhost:8080` in your browser.
- **Swagger API Documentation**: Navigate to `http://localhost:8080/docs`.

### Option B: Interactive Command-Line Interface (CLI)
Run a live multi-turn conversational session in your terminal:
```bash
PYTHONPATH=. python agent/cli.py
```
**Example CLI Prompts:**
- *"Analyze Apple revenue 2023 vs 2022"*
- *"Why did revenue decrease in FY2023?"*
- *"Compare Microsoft and Nvidia operating income for 2024"*
- *"Explain Tesla's Item 1A Risk Factors disclosures for 2023"*

---

## 🧪 Testing & Multi-Pillar Evaluation

The SEC EDGAR Natural Language Analyst evaluation pipeline implements **Google ADK Multi-Pillar Evaluation** across four distinct tiers:
1. **Deterministic Tool Trajectory (`tool_trajectory_avg_score`)**: Evaluates `IN_ORDER` exact tool invocations, argument matching, and zero hallucinated APIs.
2. **Lexical Token Overlap (`response_match_score`)**: Statistical ROUGE-1 F1 baseline measuring presence of essential financial tokens and company entities.
3. **LLM-as-a-Judge Semantic Match (`final_response_match_v2`)**: Evaluates semantic equivalence to golden reference answers via `gemini-2.5-flash`.
4. **LLM-as-a-Judge Financial Rubrics (`rubric_based_final_response_quality_v1`)**: Qualitatively scores Faithfulness, Numerical Precision, Completeness, and Conversational Isolation against strict SEC financial rubrics.

---

### 1. Pytest Unit & Integration Test Suite
Execute the complete deterministic test harness across all 5 test modules (69 tests):
```bash
make test
# or: pytest eval/
```

### 2. Parallel ADK Evaluation Runner (`eval/run_adk_eval_parallel.py`)
Run the 39-case master evaluation suite with configurable concurrency (`-p 8`):

#### Fast Offline Mocked Evaluation:
```bash
make eval-mocked
# or: python eval/run_adk_eval_parallel.py --mode mocked -p 8
```

#### Live Vertex AI Model & LLM-as-a-Judge Evaluation:
```bash
make eval-live
# or: python eval/run_adk_eval_parallel.py --mode live -p 8
```

#### Run Targeted Test Cases:
```bash
python eval/run_adk_eval_parallel.py --mode live -p 4 --cases test_001_aapl_revenue,test_003_msft_revenue,test_017_edge_zero_prior_period
```
Reports are automatically generated and saved by execution mode to [`eval/results/adk_parallel_eval_sec_edgar_analyst_master_v1_live.md`](eval/results/adk_parallel_eval_sec_edgar_analyst_master_v1_live.md) and [`eval/results/adk_parallel_eval_sec_edgar_analyst_master_v1_mocked.md`](eval/results/adk_parallel_eval_sec_edgar_analyst_master_v1_mocked.md).

### 3. Latency & Performance Profiling
System latency and execution profiling are measured across multiple operational layers:
1. **Parallel Evaluation Profiling**: `eval/run_adk_eval_parallel.py` measures precise wall-clock latency per case, overall suite throughput, and breaks down timing across phase 1 (agent trajectory inference) and phase 2 (multi-pillar metric evaluation). The generated markdown scorecard includes a dedicated `Latency (s)` column for every test case.
2. **Distributed OpenTelemetry Spans**: `agent/observability/tracer.py` traces root agent invocations, tool calling sub-spans, and SEC search roundtrips in Google Cloud Trace.
3. **Production BigQuery Telemetry Sink**: `agent/observability/telemetry_sink.py` asynchronously logs per-request token metrics (prompt tokens, response tokens, cached tokens), cache hit ratios, and millisecond latencies to BigQuery (`sec_edgar_telemetry.telemetry_events`).

---

## 🛠️ Ground-Truth Data Tools

### 1. Audit BigQuery Against SEC EDGAR XBRL
Compare all structured BigQuery rows directly against official SEC EDGAR XBRL facts (`data.sec.gov`):
```bash
PYTHONPATH=. python scripts/audit_bigquery_against_sec.py
```

### 2. Synchronize BigQuery Directly From SEC Filings
Populate or update BigQuery with audited SEC EDGAR XBRL company facts:
```bash
PYTHONPATH=. python scripts/sync_bigquery_from_sec_edgar.py
```

### 3. Recompile ADK EvalSets
Generate canonical ADK-native `.evalset.json` files from `golden_dataset.json`:
```bash
PYTHONPATH=. python eval/generate_evalset.py
```
