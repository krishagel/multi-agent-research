# Multi-Agent Research System Architecture

## Agent Interaction Diagram

```mermaid
graph TB
    User[User Query] --> UI[Gradio UI]
    UI --> RC[Research Crew<br/>Orchestrator]
    
    RC --> LR[Lead Researcher<br/>Claude Sonnet]
    
    LR -->|1. Analyzes Query| RP[Research Plan]
    RP -->|2. Creates Angles| RC
    
    RC -->|3. Spawns| SR1[Sub-Researcher 1<br/>Claude Haiku]
    RC -->|3. Spawns| SR2[Sub-Researcher 2<br/>Claude Haiku]
    RC -->|3. Spawns| SR3[Sub-Researcher 3<br/>Claude Haiku]
    RC -->|3. Spawns| SRN[Sub-Researcher N<br/>Claude Haiku]
    
    SR1 -->|4. Search| TS1[Tavily Search]
    SR2 -->|4. Search| TS2[Tavily Search]
    SR3 -->|4. Search| TS3[Tavily Search]
    SRN -->|4. Search| TSN[Tavily Search]
    
    TS1 --> Cache[(Search Cache<br/>SQLite)]
    TS2 --> Cache
    TS3 --> Cache
    TSN --> Cache
    
    SR1 -->|5. Findings| QC[Quality Controller<br/>Claude Haiku]
    SR2 -->|5. Findings| QC
    SR3 -->|5. Findings| QC
    SRN -->|5. Findings| QC
    
    QC -->|6. Evaluate| SE[Source Evaluator<br/>Claude Haiku]
    SE -->|7. Verify| FC[Fact Checker<br/>Claude Haiku]
    
    FC -->|8. If Score < 75| RC
    FC -->|8. If Score >= 75| LR
    
    LR -->|9. Synthesize| Results[Final Research Report]
    Results --> DB[(Research Database<br/>SQLite)]
    Results --> UI
    
    subgraph "Parallel Processing"
        SR1
        SR2
        SR3
        SRN
    end
    
    subgraph "Quality Assurance"
        QC
        SE
        FC
    end
    
    subgraph "Persistence Layer"
        Cache
        DB
    end
    
    TL[Thought Logger] -.->|Logs| SR1
    TL -.->|Logs| SR2
    TL -.->|Logs| SR3
    TL -.->|Logs| SRN
    TL -.->|Logs| LR
    TL -.->|Logs| QC
    TL -.->|Logs| SE
    TL -.->|Logs| FC
    
    style LR fill:#f9f,stroke:#333,stroke-width:4px
    style QC fill:#bbf,stroke:#333,stroke-width:2px
    style SE fill:#bbf,stroke:#333,stroke-width:2px
    style FC fill:#bbf,stroke:#333,stroke-width:2px
    style RC fill:#fbb,stroke:#333,stroke-width:4px
```

## Agent Workflow Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Gradio UI
    participant RC as Research Crew
    participant LR as Lead Researcher
    participant SR as Sub-Researchers
    participant QA as Quality Agents
    participant DB as Database
    
    U->>UI: Submit Query
    UI->>RC: Initialize Research
    RC->>LR: Plan Research
    LR->>LR: Analyze Query
    LR->>RC: Return Research Angles
    
    par Parallel Research
        RC->>SR: Assign Angle 1
        and
        RC->>SR: Assign Angle 2
        and
        RC->>SR: Assign Angle 3
    end
    
    SR->>SR: Generate Search Queries
    SR->>SR: Execute Searches
    SR->>SR: Analyze Results
    SR->>QA: Submit Findings
    
    QA->>QA: Evaluate Quality
    QA->>QA: Check Sources
    QA->>QA: Verify Facts
    
    alt Quality Score < 75
        QA->>RC: Request More Research
        RC->>SR: Refine Research
    else Quality Score >= 75
        QA->>LR: Approve Findings
        LR->>LR: Synthesize Results
        LR->>DB: Save Session
        LR->>UI: Return Report
        UI->>U: Display Results
    end
```

## Agent Roles and Responsibilities

```mermaid
mindmap
  root((Research System))
    Orchestration
      Research Crew
        Manages workflow
        Spawns agents
        Tracks progress
        Handles iterations
    
    Research
      Lead Researcher
        Query analysis
        Research planning
        Final synthesis
        Citation formatting
      
      Sub-Researchers
        Specialized searches
        Parallel execution
        Context-aware queries
        Source tracking
    
    Quality Control
      Quality Controller
        Research evaluation
        Gap identification
        Score calculation
        Iteration decisions
      
      Source Evaluator
        Credibility checks
        Relevance scoring
        Domain analysis
        Bias detection
      
      Fact Checker
        Claim verification
        Cross-referencing
        Contradiction detection
        Reliability scoring
    
    Infrastructure
      Thought Logger
        Real-time tracking
        Decision transparency
        Metadata capture
        Session management
      
      Search Tool
        Tavily API integration
        Result caching
        Query optimization
        Error handling
      
      Database
        Session storage
        Finding persistence
        Source tracking
        Statistics
```

## Data Flow Diagram

```mermaid
graph LR
    subgraph "Input"
        Q[User Query]
        C[Configuration]
    end
    
    subgraph "Processing"
        Q --> RP[Research Planning]
        RP --> RA[Research Angles]
        RA --> PS[Parallel Searches]
        PS --> AF[Analyzed Findings]
        AF --> QE[Quality Evaluation]
        QE --> S[Synthesis]
    end
    
    subgraph "Storage"
        PS --> SC[(Search Cache)]
        S --> RD[(Research DB)]
        RP --> TL[(Thought Logs)]
        AF --> TL
        QE --> TL
    end
    
    subgraph "Output"
        S --> FR[Final Report]
        FR --> MD[Markdown]
        FR --> JSON[JSON]
        TL --> TS[Thought Stream]
    end
    
    style Q fill:#9f9,stroke:#333,stroke-width:2px
    style FR fill:#9f9,stroke:#333,stroke-width:2px
```

## Cost and Performance Characteristics

| Agent Type | Model | Cost/1M tokens | Typical Usage | Purpose |
|------------|-------|----------------|---------------|---------|
| Lead Researcher | Claude Sonnet | $3/$15 | 2 calls per query | High-quality planning & synthesis |
| Sub-Researchers | Claude Haiku | $0.80/$4 | 3-5 calls each | Cost-effective parallel research |
| Quality Agents | Claude Haiku | $0.80/$4 | 1-2 calls each | Efficient quality control |

## Key Design Decisions

1. **Hierarchical Structure**: Lead researcher coordinates to ensure coherent output
2. **Parallel Processing**: Multiple sub-researchers work simultaneously for speed
3. **Quality Gates**: Automated quality control prevents low-quality results
4. **Iterative Refinement**: Can loop up to 3 times for better results
5. **Cost Optimization**: Expensive models only where needed
6. **Transparency**: All decisions logged for debugging and analysis
7. **Persistence**: All research saved for future reference

## Typical Research Flow Example

For a query like "What are the best practices for implementing RAG systems?":

1. **Lead Researcher** identifies 5 research angles:
   - RAG architecture patterns
   - Vector database selection
   - Chunking strategies
   - Retrieval optimization
   - Evaluation metrics

2. **5 Sub-Researchers** work in parallel, each:
   - Generating 3 search queries
   - Analyzing 15-20 search results
   - Extracting key findings

3. **Quality Controller** evaluates:
   - Coverage completeness
   - Source diversity
   - Information accuracy

4. **Source Evaluator** checks:
   - Academic papers vs blogs
   - Publication dates
   - Author credibility

5. **Fact Checker** verifies:
   - Technical claims
   - Performance metrics
   - Best practice recommendations

6. **Lead Researcher** synthesizes:
   - Executive summary
   - Detailed findings
   - Actionable recommendations
   - Cited sources

Total time: ~30-60 seconds
Total cost: ~$0.10-0.20