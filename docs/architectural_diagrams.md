# 📐 SEC EDGAR Natural Language Analyst — Updated Architectural Diagrams

This document contains the latest production-grade Mermaid diagrams for the SEC EDGAR Natural Language Analyst application. You can paste these directly into [mermaid.live](https://mermaid.live) to export ultra-high-resolution PNGs/SVGs for your slides, or view them rendered inside Antigravity and GitHub.

---

## Diagram 1: End-to-End System Architecture (ADK + Model Armor + RAG)

```mermaid
flowchart TD
    subgraph Frontend ["Presentation Layer"]
        UI["React 18 / TypeScript Web UI<br/>(Split-Pane Context & A2UI Renderer)"]
    end

    subgraph API_Security ["API & Guardrail Perimeter"]
        FastAPI["FastAPI / Cloud Run Server"]
        ModelArmorIn["Model Armor Ingress Callback<br/>(model_armor_before_model_callback)"]
        ModelArmorOut["Model Armor Egress Callback<br/>(model_armor_after_model_callback)"]
    end

    subgraph ADK_Orchestrator ["Agentic Core & Orchestration"]
        Supervisor["Root Orchestrator<br/>(google.adk.agents.llm_agent.LlmAgent)"]
        Constitution["System Constitution<br/>(agent/constitution.py)"]
        SessionStore["Persistent Session Store<br/>(agent/memory/session_store.py)"]
    end

    subgraph Tools_Subagents ["Tools & Sub-Agents"]
        BQTool["query_bigquery_financial_metrics_tool"]
        MathTool["calculate_financial_variance_tool<br/>(agent/tools/calculation_engine.py)"]
        SearchSubagent["Search Subagent<br/>(agent/subagents/search_subagent.py)"]
        ExportTool["export_financial_report<br/>(Human-in-the-Loop Gate)"]
    end

    subgraph RAG_Data ["Enterprise RAG Data Foundation"]
        BigQuery[("BigQuery Golden Tables<br/>(sec_financial_metrics)")]
        VertexSearch[("GCP Vertex AI Search DataStore<br/>(sec-10k-filings-datastore)")]
        GCS[("GCS Bucket Filings<br/>gs://sec-analyst-sec-reports/filings/")]
    end

    %% Execution Flow Connections
    UI -->|POST /api/chat| FastAPI
    FastAPI --> ModelArmorIn
    ModelArmorIn -- Prompt Clean --> Supervisor
    ModelArmorIn -- Threat Blocked --> UI
    
    Supervisor --- Constitution
    Supervisor <--> SessionStore
    
    Supervisor -->|Structured Metric Lookup| BQTool
    Supervisor -->|Variance Math Calculation| MathTool
    Supervisor -->|Qualitative 10-K Search| SearchSubagent
    Supervisor -->|Report Export| ExportTool
    
    BQTool -->|SQL Query| BigQuery
    SearchSubagent -->|Hybrid Search| VertexSearch
    VertexSearch -->|GCS URI Document Chunks| GCS
    
    Supervisor --> ModelArmorOut
    ModelArmorOut -- Sanitized Response --> UI
```

---

## Diagram 2: Agentic Execution & Tool Decision Waterfall

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Web Client
    participant API as FastAPI / ADK Runner
    participant Guard as Model Armor Guardrail
    participant Supervisor as Root Orchestrator
    participant Math as Calculation Engine
    participant SubAgent as Search Subagent
    participant RAG as Vertex AI Search & GCS

    User->>API: Submit Prompt ("Compare Tesla 2022 vs 2023 Revenue & Risks")
    API->>Guard: Sanitize Prompt Ingress (model_armor_before_model_callback)
    Guard-->>API: Pass (No Jailbreak / Injection)
    API->>Supervisor: Forward Prompt + Session Context
    
    rect rgb(235, 245, 255)
        note over Supervisor: Intent Evaluation & Tool Routing
        Supervisor->>Supervisor: Identify Structured Metrics & Qualitative Needs
        Supervisor->>Math: Execute calculate_financial_variance_tool(TSLA, Revenue, 96773, 81462)
        Math-->>Supervisor: Return VarianceResult (+18.79% Growth, +$15.31B Delta)
        
        Supervisor->>SubAgent: Invoke search_tool("Tesla 2023 business risks & MD&A")
        SubAgent->>RAG: Query Vertex AI Search DataStore (page_size=5)
        RAG-->>SubAgent: Return Filing Chunks + GCS URIs
        SubAgent-->>Supervisor: Synthesize Qualitative Excerpts & Citations
    end

    rect rgb(240, 255, 240)
        note over Supervisor: Parallel Grounded Highlighting & A2UI Assembly
        Supervisor->>Supervisor: Annotate <mark> text clauses & generate A2UI JSON Spec
    end

    Supervisor->>Guard: Sanitize Response Egress (model_armor_after_model_callback)
    Guard-->>API: Response Cleaned
    API-->>User: Grounded Narrative + Inline Citations + A2UI Chart Payload
```

---

## Diagram 3: Hybrid Search RAG Dual-Path Retrieval Waterfall

```mermaid
flowchart LR
    subgraph QueryInput ["User Query Input"]
        Q["'What were Nvidia AI R&D spend and 2023 net income margins?'"]
    end

    subgraph Router ["Query Formulation & Noise Stripping"]
        QF["formulate_vertex_search_query()<br/>Strips conversational preamble, anchors Ticker (NVDA) & Year (2023)"]
    end

    subgraph DualPath ["Dual-Path Retrieval"]
        direction TB
        Path1["Structured Path: BigQuery SQL Lookup<br/>(query_bigquery_financial_metrics_tool)"]
        Path2["Unstructured Path: Vertex AI Search<br/>(search_sec_filing_chunks_tool)"]
    end

    subgraph DataSources ["GCP Storage Layers"]
        BQ[("BigQuery Golden Financial Metrics")]
        DataStore[("Vertex AI Search DataStore<br/>(sec-10k-filings-datastore)")]
    end

    subgraph RRF_Highlight ["Ranking & Highlighting Middleware"]
        RRF["Reciprocal Rank Fusion (RRF)<br/>Merges SQL & Vector Results"]
        LLMHighlight["Parallel LLM Highlighting<br/>(annotate_grounded_highlights_with_llm)"]
    end

    subgraph Output ["Grounded Output Engine"]
        Result["Annotated <mark> Sentence Excerpts +<br/>(Source: NVDA 2023 10-K Item 7 MD&A, gs://...)"]
    end

    Q --> QF
    QF --> Path1 & Path2
    Path1 --> BQ
    Path2 --> DataStore
    BQ & DataStore --> RRF
    RRF --> LLMHighlight
    LLMHighlight --> Result
```

---

## Diagram 4: Security Perimeter & Human-In-The-Loop Approval Gate

```mermaid
stateDiagram-v2
    [*] --> IngressCheck: User Request Initiated
    
    state IngressCheck {
        [*] --> ModelArmorPromptScan
        ModelArmorPromptScan --> BlockedIngress: Injection / Jailbreak Detected
        ModelArmorPromptScan --> ApprovedIngress: Prompt Clean
    }
    
    BlockedIngress --> [*]: Return [MODEL_ARMOR_BLOCK:STAGE=INGRESS]
    
    ApprovedIngress --> AgentOrchestration: Forward to Root Orchestrator
    
    state AgentOrchestration {
        [*] --> ToolExecution
        ToolExecution --> FinancialAnalysis
        FinancialAnalysis --> CheckExportRequest
    }
    
    state CheckExportRequest <<choice>>
    CheckExportRequest --> ModelArmorEgressScan: Normal Analysis Response
    CheckExportRequest --> HITLGate: Export Report Requested
    
    state HITLGate {
        [*] --> PendingApproval: Requires Human Confirmation
        PendingApproval --> UserApproved: Human Sign-Off (human_approved = True)
        PendingApproval --> UserRejected: Action Cancelled / Denied
    }
    
    UserApproved --> ExportToGCS: Write to gs://sec-analyst-sec-reports/exports/
    UserRejected --> CancelledState: Return PENDING_HUMAN_APPROVAL Error
    ExportToGCS --> ModelArmorEgressScan
    CancelledState --> ModelArmorEgressScan
    
    state ModelArmorEgressScan {
        [*] --> ModelArmorResponseFilter
        ModelArmorResponseFilter --> BlockedEgress: Policy Violation Detected
        ModelArmorResponseFilter --> CleanOutput: Egress Approved
    }
    
    BlockedEgress --> [*]: Return [MODEL_ARMOR_BLOCK:STAGE=EGRESS]
    CleanOutput --> [*]: Render Final Grounded Answer to Client
```

---

## Diagram 5: Development Harness & Refinement Flywheel

```mermaid
flowchart TD
    subgraph Initialization ["1. Harness Initialization"]
        Specs["Product Specifications<br/>(FDE Onboarding Project.md)"]
        Const["System Constitution<br/>(agent/constitution.py)"]
        Eval["Pytest Golden Dataset<br/>(eval/golden_dataset.json)"]
    end

    subgraph Loop ["2. In-The-Loop Co-Design"]
        Schemas["Pydantic Tool Schemas<br/>(calculation_engine.py)"]
        A2UI["A2UI Visual Catalog Protocol"]
        Citations["Granular Source Citation Rules"]
    end

    subgraph Autonomous ["3. Outside-The-Loop Execution"]
        PytestRunner["Autonomous AGY Pytest Loops<br/>(pytest eval/)"]
        TraceDebug["Empirical Stack Trace Analysis"]
        AutoPatch["Self-Healing Code Modifications"]
    end

    subgraph Flywheel ["4. Refinement Flywheel"]
        IncidentLog["Runtime Incident Detection<br/>(e.g., 2025 Refusals, HTML Tables)"]
        RuleCodification["Codify Permanent Rule in Constitution<br/>(agent/constitution.py)"]
        AssertionLock["Lock Assertion in eval/run_benchmark.py"]
    end

    Specs & Const & Eval --> Schemas & A2UI & Citations
    Schemas & A2UI & Citations --> PytestRunner
    PytestRunner --> TraceDebug --> AutoPatch
    AutoPatch --> IncidentLog --> RuleCodification --> AssertionLock
    AssertionLock -->|Regression Prevention| PytestRunner
```
