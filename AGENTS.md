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
7. **Zero Hardcoding/Fallbacks**: Never hardcode ticker symbols, company maps, or fallback ticker defaults in orchestrators, tools, or frontend UI components. All company tickers must be dynamically resolved from SEC corpus metadata, BigQuery tool outputs, or explicit LLM payload parameters.
8. **Multi-Agent Worktree Isolation**: If a prompt is received while another agent thread is actively running in the main repo, a dedicated git worktree (`git worktree add -b ...`) must be created for the new prompt to avoid work overlaps and file conflict issues. See [.agents/rules/rule-worktree-isolation.md](file:///.agents/rules/rule-worktree-isolation.md).

