# 📐 SEC EDGAR Natural Language Analyst — Architectural Diagrams

This document contains the authoritative, production-grade Mermaid diagrams for the **SEC EDGAR Natural Language Analyst** application. You can paste these directly into [mermaid.live](https://mermaid.live) to export ultra-high-resolution PNGs/SVGs for presentations, or view them rendered directly in GitHub and Antigravity.

---

## Diagram 1D: Pure Unconstrained Architecture (Clean Organic Flow)

> [!TIP]
> 🎨 **Pure Diagram Assets (No Slide Frame Restraints)**:
> - **Pure Flow Vector SVG**: [`docs/architecture_diagram1_pure.svg`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_pure.svg)
> - **4K Ultra-HD PNG**: [`docs/architecture_diagram1_4k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_4k.png)
> - **8K Super-HD PNG**: [`docs/architecture_diagram1_8k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_8k.png)

```mermaid
flowchart TD
    UI["React 18 / TypeScript Web UI<br/>(Split-Pane Context & Citations)"]
    FastAPI["FastAPI REST Server<br/>(Cloud Run Gateway)"]
    AppController["AppController<br/>(Session & Context Router)"]
    SessionStore[("Persistent Session Store<br/>(Turn History Memory)")]

    RootOrchestrator["ADK Root Orchestrator (Gemini 2.5 Pro / Flash)<br/>📜 Enforces System Constitution & Math Lock"]
    Observability["Observability Core<br/>(BigQuery Telemetry & Cost Tracker)"]
    ModelArmor["Security<br/>(Model Armor Guardrail)"]

    BQTool["BigQuery SQL Tool<br/>(Audited Financials)"]
    MathTool["Variance Math Engine<br/>(YoY % Calculations)"]
    SearchSubagent["10-K Search Subagent<br/>(Item 1A Risk & Item 7 MD&A)"]
    ExportTool["HITL Export Gate<br/>(Human Approval Step)"]

    BigQuery[("BigQuery Golden Tables<br/>(sec_financial_metrics)")]
    VertexSearch[("Vertex AI Search<br/>(10-K Document Datastore)")]
    GCS[("Cloud Storage GCS<br/>(Filings & Report Exports)")]

    UI -->|POST /api/chat| FastAPI
    FastAPI --> AppController
    AppController <--> SessionStore
    AppController -->|Grounded Narrative + A2UI Spec| RootOrchestrator

    RootOrchestrator <--> Observability
    RootOrchestrator <--> ModelArmor

    RootOrchestrator --> BQTool
    RootOrchestrator --> MathTool
    RootOrchestrator --> SearchSubagent
    RootOrchestrator --> ExportTool

    BQTool --> BigQuery
    SearchSubagent --> VertexSearch
    VertexSearch -.-> GCS
    ExportTool -->|if Approved| GCS
```

---

## Diagram 1A: Executive Presentation Architecture (Capstone Slide Ready)


> [!TIP]
> 🎨 **Presentation Slide Assets**:
> - **Widescreen 16:9 SVG**: [`docs/architecture_diagram1_executive.svg`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_executive.svg)
> - **4K Ultra-HD PNG**: [`docs/architecture_diagram1_executive_4k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_executive_4k.png)
> - **8K Super-HD PNG**: [`docs/architecture_diagram1_executive_8k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_executive_8k.png)
> - **Editable PowerPoint (.pptx)**: [`docs/architecture_diagram1_editable.pptx`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_editable.pptx)

```mermaid
flowchart LR
    subgraph Tier1 ["1. Presentation Tier"]
        UI["React 18 Web UI<br/>• Split-Pane Dashboard<br/>• Grounded Citations<br/>• Dynamic A2UI Renderer"]
    end

    subgraph Tier2 ["2. API & Session Tier"]
        FastAPI["FastAPI REST Server<br/>(Cloud Run)"]
        AppController["AppController<br/>(Session & Context Router)"]
        SessionStore[("Persistent Session Store<br/>(Turn History Memory)")]
    end

    subgraph Tier3 ["3. Agentic Core & Security"]
        RootOrchestrator["ADK Root Orchestrator<br/>(Gemini 2.5 Pro / Flash)"]
        Constitution["System Constitution<br/>(Grounding & Math Rules)"]
        
        subgraph Security ["Security Perimeter"]
            ModelArmor["Model Armor Guardrail<br/>• Ingress Prompt Scan<br/>• Egress Policy Filter<br/>• Fail-Open Fallback"]
        end
        
        subgraph Telemetry ["Observability Core"]
            Observability["BigQuery Telemetry Sink<br/>& Token Cost Tracker"]
        end
    end

    subgraph Tier4 ["4. Tools & Sub-Agents Tier"]
        BQTool["BigQuery SQL Tool<br/>(Audited Financials)"]
        MathTool["Variance Math Engine<br/>(YoY % Calculations)"]
        SearchSubagent["10-K Search Subagent<br/>(Item 1A Risk & Item 7 MD&A)"]
        ExportTool["HITL Export Gate<br/>(Human Approval Step)"]
    end

    subgraph Tier5 ["5. Enterprise Data Tier"]
        BigQuery[("BigQuery Golden Tables<br/>(sec_financial_metrics)")]
        VertexSearch[("Vertex AI Search<br/>(10-K Document Datastore)")]
        GCS[("Cloud Storage GCS<br/>(Filings & Report Exports)")]
    end

    %% Direct Execution Flow Connections
    UI -->|POST /api/chat| FastAPI
    FastAPI --> AppController
    AppController <--> SessionStore
    AppController --> RootOrchestrator
    
    RootOrchestrator --- Constitution
    RootOrchestrator <--> Security
    RootOrchestrator --> Telemetry
    
    RootOrchestrator --> BQTool & MathTool & SearchSubagent & ExportTool
    
    BQTool --> BigQuery
    SearchSubagent --> VertexSearch
    VertexSearch -.-> GCS
    ExportTool -->|If Approved| GCS
    
    RootOrchestrator -->|Grounded Narrative + A2UI Spec| AppController
    AppController --> UI
```

---

## Diagram 1B: Detailed Technical Architecture (Comprehensive Code Specification)

> [!TIP]
> 🎨 **Detailed Code Assets**:
> - **Widescreen 16:9 SVG**: [`docs/architecture_diagram1_detailed.svg`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_detailed.svg)
> - **4K Ultra-HD PNG**: [`docs/architecture_diagram1_detailed_4k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_detailed_4k.png)
> - **8K Super-HD PNG**: [`docs/architecture_diagram1_detailed_8k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_detailed_8k.png)
> - **Editable PowerPoint (.pptx)**: [`docs/architecture_diagram1_detailed_editable.pptx`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_detailed_editable.pptx)

```mermaid
flowchart TD
    subgraph Presentation ["1. Presentation Layer"]
        UI["React 18 / TypeScript Web UI<br/>(agent/ui/src/)"]
    end

    subgraph API_Session ["2. API & Session Layer"]
        FastAPI["FastAPI REST Server<br/>(agent/api.py)"]
        AppController["AppController<br/>(app/app_controller.py)"]
        SessionStore["Persistent Session Store<br/>(agent/memory/session_store.py)"]
    end

    subgraph ADK_Orchestrator ["3. Agentic Core & Security (ADK Framework)"]
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

    subgraph Tools_Subagents ["4. Tools & Sub-Agents Layer"]
        BQTool["query_bigquery_financial_metrics_tool<br/>(agent/rag/bigquery_store.py)"]
        MathTool["calculate_financial_variance_tool<br/>(agent/tools/calculation_engine.py)"]
        SearchSubagent["Search Subagent & search_tool<br/>(agent/subagents/search_subagent.py)"]
        GroundingMW["LLM Grounding Middleware<br/>(annotate_grounded_highlights_with_llm)"]
        ExportTool["export_financial_report<br/>(Human-in-the-Loop Approval Gate)"]
    end

    subgraph RAG_Data ["5. Enterprise RAG Data Foundation"]
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

## Diagram 1C: System Design & Modular Architecture (Interview & Scaling Whiteboard)

> [!TIP]
> 🎨 **System Design & Scaling Assets**:
> - **Widescreen 16:9 SVG**: [`docs/architecture_diagram1_system_design.svg`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_system_design.svg)
> - **4K Ultra-HD PNG**: [`docs/architecture_diagram1_system_design_4k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_system_design_4k.png)
> - **8K Super-HD PNG**: [`docs/architecture_diagram1_system_design_8k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_system_design_8k.png)
> - **Editable PowerPoint (.pptx)**: [`docs/architecture_diagram1_system_design_editable.pptx`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/architecture_diagram1_system_design_editable.pptx)

```mermaid
flowchart LR
    subgraph Client ["1. Client Tier"]
        UI["Web Client / UI<br/>(React 18 SPA)<br/>🔄 Pluggable Mobile / Slack"]
    end

    subgraph API_Memory ["2. API & Session State"]
        Gateway["Stateless API Gateway<br/>(FastAPI / Cloud Run)"]
        Memory["Multi-Turn Session Memory<br/>🔄 Pluggable Redis / Spanner"]
    end

    subgraph Core ["3. Agentic Core & Security"]
        Orchestrator["Agentic Orchestrator Core<br/>(Google ADK + Gemini)"]
        SecurityProxy["Security Perimeter<br/>(Model Armor Proxy)<br/>🔄 Pluggable Guardrail"]
        TelemetrySink["Telemetry & Audit Sink<br/>(Async Stream)<br/>🔄 Pluggable Datadog"]
    end

    subgraph Tools ["4. Decoupled Tool Services"]
        SQLTool["Structured SQL Tool<br/>(BigQuery Metrics)"]
        MathTool["Math Variance Engine<br/>(Isolated Calculation)"]
        RAGSubagent["Qualitative RAG Subagent<br/>(Item 1A & Item 7)"]
        HITLGate["HITL Approval Gate<br/>(Human Export Gate)"]
    end

    subgraph Storage ["5. Pluggable Data Stores"]
        StructuredDB[("Analytical Database<br/>🔄 BigQuery / Snowflake")]
        VectorIndex[("Vector & Hybrid Index<br/>🔄 Vertex Search / Pinecone")]
        ObjectStore[("Object Store<br/>🔄 GCS / AWS S3")]
    end

    Client -->|HTTP/REST| Gateway
    Gateway <--> Memory
    Gateway --> Orchestrator
    Orchestrator <--> SecurityProxy
    Orchestrator --> TelemetrySink
    
    Orchestrator --> SQLTool & MathTool & RAGSubagent & HITLGate
    
    SQLTool --> StructuredDB
    RAGSubagent --> VectorIndex
    HITLGate -->|If Approved| ObjectStore
```

---

## Diagram 2: Agentic Execution & Tool Decision Waterfall

> [!TIP]
> 🎨 **Sequence Diagram Presentation Slide Assets**:
> - **Widescreen 16:9 Vector SVG**: [`docs/sequence_diagram2_gcp_light.svg`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/sequence_diagram2_gcp_light.svg)
> - **4K Ultra-HD PNG**: [`docs/sequence_diagram2_4k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/sequence_diagram2_4k.png)
> - **8K Super-HD PNG**: [`docs/sequence_diagram2_8k.png`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/sequence_diagram2_8k.png)
> - **Editable PowerPoint (.pptx)**: [`docs/sequence_diagram2_editable.pptx`](file:///Users/cvwang/Documents/gcp/sec-edgar-analyst/docs/sequence_diagram2_editable.pptx)

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
        BenchRunner["Benchmark Test Runner<br/>(pytest eval/ & run_adk_eval_parallel.py)"]
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

---

## Diagram 7: End-to-End Data Ingestion & Vertex AI Hybrid Search Architecture (PRES-02)

```mermaid
flowchart TD
    subgraph RawSources ["1. SEC EDGAR Raw Ingestion"]
        SEC["SEC EDGAR System / SEC API<br/>• Form 10-K (Annual Disclosures)<br/>• Form 10-Q (Quarterly Reports)<br/>• XBRL & HTML Filings"]
        Trigger["Eventarc / GCS Event Trigger<br/>(Automated Ingestion Pipeline)"]
        GCS_Raw[("GCS Raw Filing Bucket<br/>gs://sec-analyst-raw-filings/<br/>(Immutable Archive)")]
    end

    subgraph ParsingStage ["2. Parsing, Normalization & Chunking"]
        DocAI["Document AI & Parsing Engine<br/>• HTML/XBRL Tag Stripping<br/>• Financial Statement Table Extraction<br/>• Markdown Section Preserver"]
        Chunker["Semantic & Structural Chunker<br/>• Item 1A: Risk Factors<br/>• Item 7: MD&A<br/>• Preserves Section Headers & Footnotes"]
    end

    subgraph DualStore ["3. Dual-Path Storage Foundation"]
        BQ_Store[("BigQuery Golden Tables<br/>sec_financial_metrics<br/>• Revenue, OpInc, NetInc, EPS<br/>• Ticker & FY Partitioned")]
        GCS_Processed[("GCS Processed Chunks<br/>gs://sec-analyst-processed-chunks/<br/>(Chunked JSON & Clean MD)")]
    end

    subgraph HybridEngine ["4. Vertex AI Search Hybrid Indexing & Retrieval Engine"]
        subgraph Indexing ["Dual-Index Creation"]
            DenseEmbed["Dense Embedding Engine<br/>(text-embedding-004)<br/>• 768-dim Semantic Vectors"]
            SparseIndex["Sparse Lexical Engine<br/>(BM25 Inverted Index)<br/>• Exact Financial Term Matching"]
        end
        
        VertexDataStore[("Vertex AI Search Datastore<br/>sec-10k-datastore<br/>(Hybrid Search Enabled)")]
        
        subgraph QueryRuntime ["Runtime Hybrid Retrieval"]
            QueryFormulate["Query Formulator<br/>(Ticker + FY Metadata Anchored)"]
            DenseMatch["Vector Semantic Search<br/>(High Recall)"]
            SparseMatch["BM25 Keyword Search<br/>(Exact Financial Terms)"]
            RRF["Reciprocal Rank Fusion (RRF)<br/>& Semantic Reranking Engine"]
        end
    end

    subgraph AgentServing ["5. Real-Time Agent Serving Tier"]
        SearchAgent["10-K Search Subagent<br/>(ADK LlmAgent / AgentTool)"]
        GroundedOutput["Grounded 10-K Citations<br/>• Verbatim Snippets<br/>• Deep-Linked GCS URIs<br/>• Highlighted <mark> Passages"]
    end

    SEC --> Trigger --> GCS_Raw
    GCS_Raw --> DocAI
    DocAI -->|Structured Financial Tables| BQ_Store
    DocAI -->|Unstructured Narrative Text| Chunker
    Chunker --> GCS_Processed

    GCS_Processed --> DenseEmbed --> VertexDataStore
    GCS_Processed --> SparseIndex --> VertexDataStore

    SearchAgent --> QueryFormulate
    QueryFormulate --> DenseMatch & SparseMatch
    DenseMatch --> VertexDataStore
    SparseMatch --> VertexDataStore
    VertexDataStore --> RRF
    RRF --> GroundedOutput
    GroundedOutput --> SearchAgent
```


