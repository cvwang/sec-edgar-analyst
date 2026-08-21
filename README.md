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
│   ├── test_eval_harness.py         <- Unit & Integration Pytest Suite
│   ├── test_benchmark_framework.py  <- Benchmark Framework Verification
│   ├── test_model_armor.py          <- Security Guardrail Tests
│   ├── test_multi_thread_session.py <- Multi-Turn Session State Tests
│   ├── test_sec_corpus_rag.py       <- RAG Grounding & Citation Tests
│   ├── test_telemetry_sink.py       <- Observability Sink Tests
│   └── evalsets/
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

## 🧪 Testing & Evaluation

### 1. Pytest Unit & Integration Test Suite
Execute the complete deterministic test harness (70 tests):
```bash
PYTHONPATH=. pytest eval/
```
Or run specific test modules:
```bash
PYTHONPATH=. pytest eval/test_eval_harness.py          # Math engine & agent dispatch
PYTHONPATH=. pytest eval/test_model_armor.py           # Guardrails & PII redaction
PYTHONPATH=. pytest eval/test_sec_corpus_rag.py        # RAG retrieval & citations
PYTHONPATH=. pytest eval/test_multi_thread_session.py  # Session memory & threading
PYTHONPATH=. pytest eval/test_telemetry_sink.py        # OpenTelemetry & audit sink
```

### 2. Parallel ADK Evaluation Runner (`eval/run_adk_eval_parallel.py`)
Run the 39-case master evaluation suite with configurable concurrency:

#### Offline Fast Mocked Mode:
```bash
PYTHONPATH=. python eval/run_adk_eval_parallel.py --mode mocked -p 8
```

#### Live Vertex AI Model Evaluation:
```bash
PYTHONPATH=. python eval/run_adk_eval_parallel.py --mode live -p 8
```

#### Run Targeted Cases:
```bash
PYTHONPATH=. python eval/run_adk_eval_parallel.py --mode live -p 4 --cases test_001_aapl_revenue,test_003_msft_revenue,test_017_edge_zero_prior_period
```
Reports are automatically saved to `eval/results/adk_parallel_eval_sec_edgar_analyst_master_v1.md`.

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
