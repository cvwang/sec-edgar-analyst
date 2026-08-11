# 📐 SEC EDGAR Natural Language Analyst — Architectural Diagrams

This document contains the authoritative, production-grade Mermaid diagrams for the **SEC EDGAR Natural Language Analyst** application. You can paste these directly into [mermaid.live](https://mermaid.live) to export ultra-high-resolution PNGs/SVGs for presentations, or view them rendered directly in GitHub and Antigravity.

---

## Diagram 1: End-to-End System Architecture (ADK + Model Armor + RAG + Telemetry)

> [!TIP]
> 🎨 **Presentation Slide SVG Asset**: A widescreen 16:9 vector SVG file aligned with Google Cloud Light Theme is available at [`docs/images/architecture_diagram1_gcp_light.svg`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/images/architecture_diagram1_gcp_light.svg).

```mermaid
flowchart TD
    subgraph Presentation ["Presentation Layer"]
        UI["React 18 / TypeScript Web UI<br/>(Split-Pane Context & A2UI Renderer)"]
    end

    subgraph API_Session ["API & Session Management Layer"]
        FastAPI["FastAPI REST Server<br/>(agent/api.py)"]
        AppController["AppController<br/>(app/app_controller.py)"]
        SessionStore["Persistent Session Store<br/>(agent/memory/session_store.py)"]
    end

    subgraph ADK_Orchestrator ["Agentic Core & Orchestration Layer"]
        RootOrchestrator["RootOrchestrator<br/>(agent/root_orchestrator.py)"]
        ADK_Runner["Google ADK Runner & LlmAgent<br/>(google.adk.runners.Runner)"]
        Constitution["System Constitution<br/>(agent/constitution.py)"]
        
        subgraph Guardrails ["Model Armor Security Guardrails"]
            ModelArmorIn["Ingress Guardrail Callback<br/>(model_armor_before_model_callback)"]
            ModelArmorOut["Egress Guardrail Callback<br/>(model_armor_after_model_callback)"]
            ModelArmorAPI[("GCP Model Armor API / Fail-Open Fallback")]
        end
        
        subgraph Observability ["Observability Core"]
            TelemetrySink["BigQuery Telemetry Sink<br/>(agent/observability/telemetry_sink.py)"]
            CostTracker["Token Cost Tracker<br/>(agent/observability/cost_tracker.py)"]
            Tracer["OpenTelemetry Tracer<br/>(agent/observability/tracer.py)"]
        end
    end

    subgraph Tools_Subagents ["Tools & Sub-Agents Layer"]
        BQTool["query_bigquery_financial_metrics_tool<br/>(agent/rag/bigquery_store.py)"]
        MathTool["calculate_financial_variance_tool<br/>(agent/tools/calculation_engine.py)"]
        SearchSubagent["Search Subagent & search_tool<br/>(agent/subagents/search_subagent.py)"]
        GroundingMW["LLM Grounding Middleware<br/>(annotate_grounded_highlights_with_llm)"]
        ExportTool["export_financial_report<br/>(Human-in-the-Loop Approval Gate)"]
    end

    subgraph RAG_Data ["Enterprise RAG Data Foundation"]
        BigQuery[("BigQuery Golden Tables<br/>(sec_financial_metrics)")]
        VertexSearch[("GCP Vertex AI Search DataStore<br/>(sec-10k-filings-datastore)")]
        GCSFilings[("GCS Bucket Filings<br/>gs://sec-analyst-sec-reports/filings/")]
        GCSExports[("GCS Bucket Exports<br/>gs://sec-analyst-sec-reports/exports/")]
    end

    %% Execution Flow Connections
    UI -->|POST /api/chat| FastAPI
    FastAPI --> AppController
    AppController <-->|Load / Save History & Ticker Context| SessionStore
    AppController -->|run_analysis| RootOrchestrator
    
    RootOrchestrator --> ADK_Runner
    ADK_Runner --- Constitution
    
    ADK_Runner -->|Before LLM Call| ModelArmorIn
    ModelArmorIn <--> ModelArmorAPI
    
    ADK_Runner -->|Structured Financial Metrics| BQTool
    ADK_Runner -->|Deterministic Variance Math| MathTool
    ADK_Runner -->|Qualitative 10-K Search| SearchSubagent
    ADK_Runner -->|Report Export Gate| ExportTool
    
    BQTool -->|SQL Metrics Query| BigQuery
    SearchSubagent -->|Hybrid Search| VertexSearch
    VertexSearch -->|GCS URI Document Chunks| GCSFilings
    SearchSubagent --> GroundingMW
    
    ExportTool -->|If Human Approved| GCSExports
    
    ADK_Runner -->|After LLM Call| ModelArmorOut
    ModelArmorOut <--> ModelArmorAPI
    
    RootOrchestrator --> TelemetrySink & CostTracker & Tracer
    RootOrchestrator -->|Grounded Narrative + A2UI Payload| AppController
    AppController --> FastAPI --> UI
```

---

## Diagram 2: Agentic Execution & Tool Decision Waterfall

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Web Client
    participant API as FastAPI / AppController
    participant Store as Persistent Session Store
    participant Orch as RootOrchestrator (ADK)
    participant Guard as Model Armor Guardrail
    participant Math as Calculation Engine
    participant BQ as BigQuery RAG Tool
    participant SubAgent as Search Subagent / RAG
    participant Telemetry as BigQuery Telemetry Sink

    User->>API: Submit Prompt ("Compare Tesla 2022 vs 2023 Revenue & Risks")
    API->>Store: Get Session History & Extract Active Ticker Context ("TSLA")
    Store-->>API: Active Context Summary
    API->>Orch: run_analysis(prompt, context_summary)
    
    rect rgb(235, 245, 255)
        note over Orch, Guard: Step 1: Model Armor Ingress Scan
        Orch->>Guard: model_armor_before_model_callback(llm_request)
        Guard-->>Orch: Prompt Approved (or Graceful Fail-Open Fallback)
    end
    
    rect rgb(255, 250, 235)
        note over Orch, SubAgent: Step 2: Agentic Tool Execution Waterfall
        Orch->>BQ: query_bigquery_financial_metrics_tool(TSLA, 2022-2023)
        BQ-->>Orch: Financial Metrics JSON (Revenue: $81.46B -> $96.77B)
        
        Orch->>Math: calculate_financial_variance_tool(TSLA, Revenue, 96773, 81462)
        Math-->>Orch: VarianceResult (+18.79% Growth, +$15.31B Delta, Math Proof)
        
        Orch->>SubAgent: search_tool("Tesla 2023 business risks & MD&A")
        SubAgent-->>Orch: Grounded Filing Chunks + GCS URIs + LLM Highlights
    end

    rect rgb(240, 255, 240)
        note over Orch, Guard: Step 3: Model Armor Egress Scan & Response Assembly
        Orch->>Guard: model_armor_after_model_callback(llm_response)
        Guard-->>Orch: Response Approved
        Orch->>Orch: Assemble Grounded Narrative (<mark> tags) + A2UI Visual Payload
    end

    Orch->>Telemetry: Log Telemetry Event & Track Token Costs
    Orch-->>API: Complete Analysis Result JSON
    API->>Store: Save Session Turn & Response Metadata
    API-->>User: Grounded Narrative + Inline Citations + A2UI Chart/Table Specs
```

---

## Diagram 3: Hybrid Search RAG Dual-Path Retrieval Waterfall

```mermaid
flowchart LR
    subgraph QueryInput ["User Query Input"]
        Q["'What were Nvidia AI R&D spend and 2023 net income margins?'"]
    end

    subgraph Router ["Query Formulation & Metadata Filtering"]
        QF["formulate_vertex_search_query()<br/>Strips conversational preamble, anchors Ticker (NVDA) & Year (2023)"]
    end

    subgraph DualPath ["Dual-Path RAG Retrieval Engine"]
        direction TB
        Path1["Structured Path: BigQuery SQL Lookup<br/>(query_bigquery_financial_metrics_tool)"]
        Path2["Unstructured Path: Vertex AI Search<br/>(search_sec_filing_chunks_tool)"]
    end

    subgraph DataSources ["GCP Data Foundation"]
        BQ[("BigQuery Golden Financial Metrics")]
        DataStore[("Vertex AI Search DataStore<br/>(sec-10k-filings-datastore)")]
        GCS[("GCS SEC 10-K Filings<br/>gs://sec-analyst-sec-reports/filings/")]
    end

    subgraph Ranking_Highlight ["RAG Processing & Highlighting Middleware"]
        Consolidate["Consolidate Passage Chunks<br/>(consolidate_grounded_chunks)"]
        LLMHighlight["Parallel LLM Sentence Highlighting<br/>(annotate_grounded_highlights_with_llm)"]
    end

    subgraph Output ["Grounded Response Engine"]
        Result["Annotated <mark> Sentence Excerpts +<br/>(Source: NVDA 2023 10-K Item 7 MD&A, GCS Link) +<br/>A2UI Visual Specification Payload"]
    end

    Q --> QF
    QF --> Path1 & Path2
    Path1 --> BQ
    Path2 --> DataStore
    DataStore -.-> GCS
    BQ & DataStore --> Consolidate
    Consolidate --> LLMHighlight
    LLMHighlight --> Result
```

---

## Diagram 4: Security Perimeter & Human-In-The-Loop Approval Gate

```mermaid
stateDiagram-v2
    [*] --> IngressCheck: User Request Received
    
    state IngressCheck {
        [*] --> ModelArmorPromptScan
        ModelArmorPromptScan --> IngressBlocked: Threat / Injection Detected
        ModelArmorPromptScan --> IngressApproved: Prompt Sanitized & Clean
        ModelArmorPromptScan --> FailOpenPass: API Outage (Graceful Fail-Open)
    }
    
    IngressBlocked --> [*]: Return [MODEL_ARMOR_BLOCK:STAGE=INGRESS]
    
    IngressApproved --> AgentOrchestration: Dispatch to ADK RootOrchestrator
    FailOpenPass --> AgentOrchestration: Dispatch to ADK RootOrchestrator
    
    state AgentOrchestration {
        [*] --> ToolExecution
        ToolExecution --> FinancialAnalysis
        FinancialAnalysis --> CheckExportRequest
    }
    
    state CheckExportRequest <<choice>>
    CheckExportRequest --> ModelArmorEgressScan: Normal Analysis Response
    CheckExportRequest --> HITLGate: Export Report Requested (export_financial_report)
    
    state HITLGate {
        [*] --> PendingApproval: Paused (human_approved = False)
        PendingApproval --> UserApproved: Human Sign-Off (human_approved = True)
        PendingApproval --> UserRejected: Request Cancelled / Denied
    }
    
    UserApproved --> ExportToGCS: Write to gs://sec-analyst-sec-reports/exports/
    UserRejected --> CancelledState: Return PENDING_HUMAN_APPROVAL Status
    ExportToGCS --> ModelArmorEgressScan
    CancelledState --> ModelArmorEgressScan
    
    state ModelArmorEgressScan {
        [*] --> ModelArmorResponseFilter
        ModelArmorResponseFilter --> EgressBlocked: Leak / Policy Violation Detected
        ModelArmorResponseFilter --> EgressApproved: Response Sanitized & Clean
        ModelArmorResponseFilter --> FailOpenEgressPass: API Outage (Graceful Fail-Open)
    }
    
    EgressBlocked --> [*]: Return [MODEL_ARMOR_BLOCK:STAGE=EGRESS]
    EgressApproved --> [*]: Deliver Grounded Narrative & Visuals to Web Client
    FailOpenEgressPass --> [*]: Deliver Grounded Narrative & Visuals to Web Client
```

---

## Diagram 5: Evaluation Framework & Continuous Refinement Flywheel

```mermaid
flowchart TD
    subgraph GroundTruth ["1. Evaluation Benchmark Ground Truth"]
        GoldenDS["Pytest Golden Dataset<br/>(eval/golden_dataset.json)"]
        MasterEvalset["Master Analyst EvalSet<br/>(evalsets/sec_edgar_analyst_master.evalset.json)"]
        Constitution["System Constitution<br/>(agent/constitution.py)"]
    end

    subgraph ArchitectureSpecs ["2. Deterministic & RAG Standards"]
        Engine["Calculation Engine Rules<br/>(agent/tools/calculation_engine.py)"]
        A2UI["A2UI Visual Component Specs<br/>(MetricsChart & FinancialTable)"]
        CitationRules["100% Grounded Citation Protocol"]
    end

    subgraph EvaluationSuite ["3. Evaluation Suite Execution"]
        BenchRunner["Benchmark Test Runner<br/>(pytest eval/run_benchmark.py)"]
        TrajectoryEval["ADK Native Trajectory Evaluation<br/>(EVAL-05 ADK Test Harness)"]
        PerformanceProfile["Performance & Latency Profiling<br/>(EVAL-07 Latency Benchmarks)"]
    end

    subgraph RefinementFlywheel ["4. Continuous Refinement Flywheel"]
        IncidentLog["Runtime Incident Detection<br/>(e.g., Year Refusals, Ticker Hardcoding)"]
        ConstitutionPatch["Codify Rule in System Constitution<br/>(agent/constitution.py)"]
        AssertionLock["Lock Strict Assertion in Eval Harness"]
        ZeroRegression["Zero-Regression Lock in CI/CD"]
    end

    GoldenDS & MasterEvalset & Constitution --> Engine & A2UI & CitationRules
    Engine & A2UI & CitationRules --> BenchRunner & TrajectoryEval & PerformanceProfile
    BenchRunner & TrajectoryEval & PerformanceProfile --> IncidentLog
    IncidentLog --> ConstitutionPatch --> AssertionLock --> ZeroRegression
    ZeroRegression -->|Continuous Assertion Protection| BenchRunner
```

---

## Diagram 6: Multi-Turn Memory & Target Ticker Context Propagation

```mermaid
flowchart TD
    subgraph Turn1 ["Turn 1: Explicit Ticker Query"]
        User1["User: 'Analyze Apple FY2023 revenue vs FY2022'"]
        AppCtrl1["AppController.dispatch_query()"]
        Orch1["RootOrchestrator runs analysis for 'AAPL'"]
        Store1["SessionStore saves turn with ticker='AAPL' in metadata"]
        Resp1["Agent returns AAPL revenue variance narrative + A2UI payload"]
    end

    subgraph Turn2 ["Turn 2: Follow-up Query without Explicit Ticker"]
        User2["User: 'What are the main risk factors?'"]
        AppCtrl2["AppController extracts recent turns from SessionStore"]
        ContextExtractor["Context Summarizer detects previous ticker 'AAPL'"]
        ContextInject["Inject Context Header:<br/>'ACTIVE CONVERSATION CONTEXT: Target company is AAPL'"]
        Orch2["RootOrchestrator resolves query against AAPL 10-K Item 1A"]
        Resp2["Agent returns AAPL risk factor analysis with grounded citations"]
    end

    User1 --> AppCtrl1 --> Orch1 --> Store1 --> Resp1
    Resp1 -.-> User2
    User2 --> AppCtrl2 --> ContextExtractor --> ContextInject --> Orch2 --> Resp2
```

