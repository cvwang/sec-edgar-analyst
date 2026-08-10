# Technical Specification: SEC EDGAR Natural Language Analyst

## Core Components to Implement

### 1. Calculation Engine (`agent/tools/calculation_engine.py`)
- Deterministic calculation function for Revenue, Operating Income, and Net Income variance.
- Calculates absolute change and percentage change: `((current - prior) / prior) * 100`.
- Strict Pydantic input (`VarianceRequest`) and output (`VarianceResult`) models.
- Guided error handling to return actionable feedback to the LLM if metrics are missing or invalid.

### 2. Web App Controller & ADK Root Orchestrator
- **`app/app_controller.py`**: Defines `AppController`, managing `PersistentSessionStore`, context propagation, and request dispatching.
- **`agent/root_orchestrator.py`**: Defines ADK `RootOrchestrator` (`LlmAgent` & `Runner`), owning tools (`search_tool`, `calculate_financial_variance_tool`, `query_bigquery_financial_metrics_tool`). Standalone testable with zero FastAPI dependencies.
- Routes complex reasoning prompts to Gemini 2.5 Pro and tool/eval calls to Gemini 3.5 Flash.
- Implements human-in-the-loop approval hook before executing external export calls.

### 3. System Constitution & Prompting (`agent/constitution.py`)
- Defines persona, domain knowledge rules, and strict grounding constraints.
- Rule: 100% agreement between reported numbers and calculation engine outputs; refuse external knowledge for financial figures.

### 4. Observability & PII Scrubbing (`agent/observability/`)
- Structured JSON logging capturing `intent` (before tool execution) and `outcome` (after tool execution).
- OpenTelemetry span exports for request tracing.
- Regex/Scrubber module (`pii_scrubber.py`) to redact sensitive data (SSNs, accounts, API keys) before logging or storage.

### 5. Evaluation Harness (`eval/`)
- `golden_dataset.json`: Golden test cases with expected calculation values and 10-K grounded explanations.
- `test_eval_harness.py`: Pytest suite evaluating narrative faithfulness and numerical accuracy using LLM-as-a-judge.

### 6. Infrastructure as Code (`terraform/`)
- `main.tf`: Basic Terraform configuration for Cloud Run service, Secret Manager secret versions, and Cloud Storage buckets.
