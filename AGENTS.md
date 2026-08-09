# Agent Guidelines & Workspace Rules

This repository defines workspace rules for AI agents operating on the **SEC EDGAR Natural Language Analyst** codebase.

Full detailed rules and behavioral guidelines are located in:
- [.agents/rules/project_rules.md](file:///.agents/rules/project_rules.md)
- [.agents/rules/project_engineering_standards.md](file:///.agents/rules/project_engineering_standards.md)

## Authoritative Sources of Truth
All requirements, specifications, and scope decisions MUST be evaluated against:
1. [`FDE Onboarding Project.md`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/FDE%20Onboarding%20Project.md)
2. [`fsi_scoping.md`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/fsi_scoping.md)
3. [`fsi_tdd.md`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/fsi_tdd.md)

## Quick Summary
1. **Sources of Truth**: Always align implementation with `FDE Onboarding Project.md`, `fsi_scoping.md`, and `fsi_tdd.md`.
2. **Deterministic Calculations**: Always use the deterministic calculation engine (`agent/tools/calculation_engine.py`) for quantitative financial calculations.
3. **ADK Framework**: Follow Google Agent Development Kit (ADK) patterns when creating or modifying orchestrators, sub-agents, and tools in `agent/`.
4. **Testing**: Run pytest (`pytest eval/`) to ensure no regressions against the evaluation harness and golden dataset.
5. **Secrets**: Use `.env` or environment configuration; never hardcode credentials.
6. **Git Commits**: Never commit code updates automatically. Only commit changes when explicitly instructed by the user.
7. **Zero Hardcoding/Fallbacks**: Never hardcode ticker symbols, company maps, fallback ticker defaults, or fallback fiscal years (e.g., defaulting to `2023`, `[2023]`, or `current_year=2023`) in orchestrators, tools, API schemas, or frontend UI components. All company tickers and target fiscal years must be dynamically resolved from SEC corpus metadata, BigQuery tool outputs, or explicit user query payloads.
8. **Git Branching & Multi-Agent Worktree Flow**: When a new prompt or feature request is received:
   - If the main repository folder is **unused (idle)**, create a new feature branch directly in the main repository (`git checkout -b feature/...`).
   - If the main repository folder is **in use** (another thread or active task is operating on a branch), create a dedicated Git worktree (`git worktree add -b feature/... ../<worktree-dir> main`) for task isolation.
   See [.agents/rules/rule-worktree-isolation.md](file:///.agents/rules/rule-worktree-isolation.md).

