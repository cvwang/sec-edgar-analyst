# Workspace Rules for SEC EDGAR Natural Language Analyst

Note: Engineering standards defined in [.agents/rules/project_engineering_standards.md](file:///.agents/rules/project_engineering_standards.md) apply to all work in this repository.

## Project Overview & Architecture
- **Framework**: Google Agent Development Kit (ADK) (`RootOrchestrator`, sub-agents, custom tools).
- **Core Goal**: Agentic financial analyst automating financial variance analysis (Revenue, Operating Income, Net Income) and SEC 10-K filing tracking.
- **Sources of Truth**: The authoritative sources of truth for all project requirements, architectural design decisions, and scope are:
  1. [`FDE Onboarding Project.md`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/FDE%20Onboarding%20Project.md)
  2. [`fsi_scoping.md`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/fsi_scoping.md)
  3. [`fsi_tdd.md`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/fsi_tdd.md)
- **Directory Structure**:
  - `agent/`: Core agent code including orchestrator, tools (`calculation_engine`, `sec_retriever`), context caching, guardrails, and observability.
  - `eval/`: Evaluation harness and golden dataset (`test_eval_harness.py`, `golden_dataset.json`).
  - `terraform/`: Infrastructure as Code configurations.
  - `scripts/`: Operational and deployment scripts.

## Coding Standards & Conventions
- **Language**: Python 3.10+.
- **Type Hints**: Use explicit type annotations for all function signatures and tool definitions.
- **Math & Calculations**: Always route quantitative variance calculations through the deterministic `calculation_engine` tool instead of relying on LLM internal math.
- **Async & Performance**: Ensure I/O bound operations (SEC filing retrieval, API calls) use async paradigms where applicable.

## Agent Development & ADK Practices
- **Tool Definitions**: Tool functions in `agent/tools/` must have clear, accurate docstrings and type definitions, as ADK uses these for tool declaration and LLM schema generation.
- **Observability**: Maintain OpenTelemetry / Cloud Trace tracing and structured JSON logging across sub-agents and tool calls.
- **PII & Data Guardrails**: Pass raw text through `pii_scrubber` when processing user input or external filing data if sensitive data may be present.

## Testing & Verification
- **Pytest**: Run test suites using `pytest` before finalizing changes (`pytest eval/`).
- **Evaluation Harness**: Ensure changes to agent tools or prompt routing do not regress scores against `eval/golden_dataset.json`.
- **Raw Output Verification Standard**: Whenever asked to run a command, show output, or confirm API/test behavior, always report the actual raw command output rather than a paraphrase or summary. If something fails or cannot be verified, state the concrete result plainly.


## Dynamic Data & Zero Hardcoding Rules
- **No Hardcoded Tickers or Fallback Years**: Never hardcode company ticker symbols (e.g. AAPL, NVDA, MSFT), static company mapping dictionaries, fallback ticker defaults, or fallback fiscal years (e.g. defaulting to `2023`, `[2023]`, or `current_year=2023`) in orchestrators, tools, API schemas, or frontend UI components. All company tickers and target fiscal years must be dynamically parsed from SEC corpus metadata, BigQuery tool outputs, or explicit user query payloads.

## Git & Version Control
- **No Automatic Commits**: Code updates must never be committed automatically. Only commit changes when explicitly instructed by the user.
- **Git Branching & Multi-Agent Worktree Flow**:
  - **Main Repo Unused (Idle)**: Create a dedicated feature branch directly in the main repository (`git checkout -b feature/<task-name>`).
  - **Main Repo In Use (Active Multi-Agent)**: Create a dedicated Git worktree (`git worktree add -b feature/<task-name> ../<worktree-dir> main`) to isolate edits, dependencies, dev servers, and test runs.
  See [.agents/rules/rule-worktree-isolation.md](file:///.agents/rules/rule-worktree-isolation.md).


