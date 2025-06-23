#!/usr/bin/env python3
"""Generate PNG diagrams from Mermaid definitions using mermaid-cli."""

import subprocess
import os
from pathlib import Path

def generate_mermaid_diagram(mermaid_code: str, output_file: str, title: str = ""):
    """Generate a PNG from Mermaid code."""
    # Create temp file with mermaid code
    temp_file = f"temp_{os.path.basename(output_file)}.mmd"
    
    # Add title if provided
    if title:
        mermaid_code = f"---\ntitle: {title}\n---\n{mermaid_code}"
    
    with open(temp_file, 'w') as f:
        f.write(mermaid_code)
    
    # Generate PNG using mermaid-cli
    try:
        subprocess.run([
            'mmdc', '-i', temp_file, '-o', output_file,
            '-t', 'dark', '-b', 'transparent'
        ], check=True)
        print(f"✓ Generated {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error generating {output_file}: {e}")
    except FileNotFoundError:
        print("✗ mermaid-cli not found. Install with: npm install -g @mermaid-js/mermaid-cli")
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)

# Define diagrams
diagrams = {
    "agent_interaction.png": {
        "title": "Multi-Agent Research System Architecture",
        "code": """graph TB
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
    style RC fill:#fbb,stroke:#333,stroke-width:4px"""
    },
    
    "workflow_sequence.png": {
        "title": "Agent Workflow Sequence",
        "code": """sequenceDiagram
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
    end"""
    },
    
    "data_flow.png": {
        "title": "Data Flow Through the System",
        "code": """graph LR
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
    style FR fill:#9f9,stroke:#333,stroke-width:2px"""
    }
}

# Create docs directory if it doesn't exist
Path("docs").mkdir(exist_ok=True)

# Generate all diagrams
print("Generating Mermaid diagrams...")
for filename, diagram in diagrams.items():
    output_path = f"docs/{filename}"
    generate_mermaid_diagram(diagram["code"], output_path, diagram["title"])

print("\nDiagram generation complete!")
print("\nIf generation failed, you can:")
print("1. Install mermaid-cli: npm install -g @mermaid-js/mermaid-cli")
print("2. Use online tool: https://mermaid.live/")
print("3. View markdown file: docs/agent_architecture.md")