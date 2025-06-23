# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-agent AI research system that uses CrewAI to orchestrate multiple Claude models (via AWS Bedrock) to conduct comprehensive research on any topic. The system employs a hierarchical architecture with a lead researcher (Claude Sonnet) coordinating multiple sub-researchers (Claude Haiku) who work in parallel to investigate different aspects of a research question.

## Key Commands

### Environment Setup
```bash
# Install dependencies using uv (fast Python package manager)
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your Tavily API key and AWS credentials
```

### Running the Application
```bash
# Launch the Gradio web interface (http://localhost:7860)
uv run python main.py

# Run a test research query
uv run python test_research.py
```

### Development Commands
```bash
# Check for missing imports or syntax errors
uv run python -m py_compile agents/*.py src/*.py ui/*.py tools/*.py

# Monitor thought logs in real-time (while app is running)
tail -f data/thought_logs/thoughts_*.jsonl | jq '.'

# View architecture diagrams
open docs/view_architecture.html
```

## Architecture

The codebase follows a modular architecture:

### Visual Architecture Diagrams
- **Interactive Diagrams**: View `docs/view_architecture.html` in a browser
- **Markdown Documentation**: See `docs/agent_architecture.md` for detailed diagrams
- **Update Diagrams**: When making structural changes to agents, update the Mermaid diagrams
- **Key Diagrams**:
  - Agent Interaction Overview - Shows all agents and their connections
  - Workflow Sequence - Step-by-step process flow
  - Data Flow - How information moves through the system

### Code Structure

- **`/agents/`**: Core agent implementations
  - `research_crew.py`: Main orchestration logic that coordinates all agents
  - `lead_researcher.py`: Plans research strategy and synthesizes findings (uses Claude Sonnet)
  - `sub_researcher.py`: Conducts specialized searches on specific angles (uses Claude Haiku)
  - `base_agent.py`: Shared base class for all agents
  - `quality_controller.py`: Evaluates research quality and identifies gaps
  - `source_evaluator.py`: Assesses credibility and relevance of sources
  - `fact_checker.py`: Verifies claims and cross-references information

- **`/src/`**: Infrastructure components
  - `config.py`: Pydantic-based configuration management with validation
  - `bedrock_client.py`: AWS Bedrock client with credential chain support
  - `thought_logger.py`: Thread-safe centralized thought logging system
  - `research_database.py`: SQLite database for persistent research history
  - `security.py`: Security utilities for path validation and input sanitization
  - `exceptions.py`: Custom exception hierarchy for better error handling

- **`/tools/`**: External integrations
  - `search_tool.py`: Tavily search API with SQLite caching
  - `crewai_search_tool.py`: CrewAI-compatible wrapper for search functionality

- **`/ui/`**: User interface
  - `gradio_app.py`: Web-based UI with real-time progress tracking and thought stream display

- **`/config/`**: Configuration files
  - `models.yaml`: Model selection and pricing configuration

## Key Technical Details

1. **Model Usage**:
   - Lead Researcher: Claude 3 Sonnet (more capable, higher cost)
   - Sub-Researchers: Claude 3 Haiku (faster, lower cost)
   - Models are accessed via AWS Bedrock
   - Supports AWS credential chain (IAM roles, env vars, config files)

2. **Caching System**:
   - SQLite database stores search results to minimize API calls
   - Located at `search_cache.db`

3. **Cost Management**:
   - Real-time cost tracking during research
   - Configurable budget limits in `.env`
   - Typical costs: $0.05-$0.20 per research query

4. **Parallel Processing**:
   - 3-5 sub-researchers work concurrently
   - Uses CrewAI's built-in parallelization

5. **Output Formats**:
   - Results saved as both JSON and Markdown
   - Stored in `data/research_output/` directory

6. **Thought Logging System**:
   - Real-time visibility into AI reasoning via `ThoughtLogger`
   - Thoughts categorized by type: planning, searching, analyzing, synthesizing
   - Logs stored in `data/thought_logs/` as JSONL files
   - UI provides live thought stream with filtering capabilities
   - Each thought includes timestamp, agent ID, confidence level, and metadata
   - Export functionality for post-research analysis
   - Session management clears thoughts when starting new research

7. **Persistent Research Database**:
   - SQLite database stores complete research history
   - Tables: research_sessions, research_findings, research_sources, search_queries
   - Browse past research sessions in "Research History" tab
   - Search functionality for finding past research
   - Export sessions as JSON
   - Database statistics tracking

8. **Enhanced Research Quality**:
   - **Definitive Conclusions**: Executive summaries with concrete answers
   - **Source Citations**: All findings include source URLs and relevance scores
   - **Structured Synthesis**: Key findings, recommendations, risk assessments
   - **Search Results Tab**: View all search results during research
   - Filter by researcher, relevance, or chronological order

## Development Notes

- **Python Version**: 3.11 (specified in `.python-version`)
- **Package Manager**: uv (not pip) - ensure `uv sync` for dependencies
- **No formal testing framework** - tests are run directly via `uv run python test_research.py`
- **No linting/formatting tools** configured - maintain consistent style with existing code
- **Environment Variables**: All configuration via `.env` file (see `.env.example`)

## Common Tasks

### Adding a New Agent
1. Create new agent class in `/agents/` inheriting from `BaseAgent`
2. Define the agent's role, goal, and backstory
3. Implement thought logging in key methods using `self.log_thought()`
4. Integrate into `ResearchCrew` in `research_crew.py`
5. Update architecture diagrams in `docs/` to include the new agent

### Modifying Search Behavior
- Edit `tools/search_tool.py` to adjust search parameters
- Cache behavior can be modified in the SQLAlchemy session configuration

### Changing Models
- Update `config/models.yaml` with new model IDs
- Ensure AWS Bedrock access for new models
- Adjust prompts in agent classes if needed for different models

### UI Modifications
- Gradio interface is in `ui/gradio_app.py`
- Add new tabs or components as needed
- Progress tracking uses Gradio's built-in mechanisms
- Thought stream display refreshes every 2 seconds during research
- UI Tabs:
  - **Research**: Main query input and results
  - **Settings**: Model configuration
  - **Usage Statistics**: Cost tracking and history
  - **Research Process**: Real-time thought stream
  - **Search Results**: All search results from current research
  - **Research History**: Browse past research sessions

### UI Features
- **Dynamic Cost Estimation**: Updates in real-time as you type and adjust settings
- **Clickable Citations**: All source citations are formatted as clickable markdown links
  - Inline citations [1], [2] are now clickable links to sources (Fixed 2025-06-22)
- **Configurable Researchers**: Slider uses values from models.yaml (min: 4, max: 20, default: 7)
- **Session Selection**: Click on any past research session to view details
  - Fixed SelectData event handling for proper row selection (Fixed 2025-06-22)
- **Detailed Synthesis**: Balanced between concrete answers and sufficient explanation
- **Security Hardening**: Input validation, path protection, and usage monitoring (Added 2025-06-22)

### Analyzing Research Behavior
- Check the "Research Process" tab in the UI for real-time AI thoughts
- Filter thoughts by type (planning, searching, analyzing, etc.) or by agent
- Export thought logs using the UI button for detailed analysis
- Review thought logs in `data/thought_logs/` directory
- Use `tail -f data/thought_logs/thoughts_*.jsonl | jq '.'` to monitor in terminal

### Debugging Search Issues
- Add `[DEBUG]` to your query to enable debug mode
- Debug mode shows:
  - Tavily API key validation
  - Full search requests and responses
  - Detailed error messages with stack traces
  - Search result metadata (scores, domains, cache hits)
- Check console output for [DEBUG] messages when running with debug mode

### Quality Control Features
- **Quality Controller**: Evaluates research plans (score threshold: 70/100)
- **Source Evaluator**: Assesses credibility and relevance of sources
- **Fact Checker**: Verifies claims and cross-references information
- **Iterative Research**: Automatically refines research up to 3 iterations based on quality scores
- **Decision Transparency**: All decisions include rationale and criteria in thought logs
- **Context-Aware Queries**: Sub-researchers adapt queries based on previous findings
- Research findings are evaluated for completeness and accuracy
- Suggestions for improvements are logged in the thought stream

### Advanced Features Added
1. **Iterative Research Loop**:
   - Quality threshold: 75/100 for proceeding to synthesis
   - Maximum 3 iterations of refinement
   - Targeted research on missing aspects
   - Progress tracking throughout iterations

2. **Fact Checking**:
   - Automated claim extraction and verification
   - Cross-reference checking between sources
   - Contradiction detection
   - Reliability scoring for research findings

3. **Decision Transparency**:
   - All agents log decision rationale
   - Selection criteria exposed in metadata
   - Quality scoring breakdowns
   - Next steps clearly indicated

4. **Context-Aware Search**:
   - Adaptive query generation based on findings
   - Avoids duplicate searches
   - Follows up on insufficient results
   - Maximum search efficiency

### Security Features (Added 2025-06-22)
1. **Credential Protection**:
   - Environment variables for all sensitive data
   - AWS credential chain support (IAM roles preferred)
   - No hardcoded secrets in codebase
   - API key masking in debug output

2. **Input Validation**:
   - Path traversal protection for all file operations
   - User input sanitization to prevent injection
   - Filename sanitization for generated files
   - URL validation for external resources

3. **Usage Monitoring**:
   - Track API usage with search_count
   - Monitor against Tavily's monthly limit (1000/month)
   - Check usage statistics in the UI

4. **Error Handling**:
   - Custom exception types for specific errors
   - Sensitive data redacted from error messages
   - Proper resource cleanup with context managers

### Security Best Practices
- Always use `security.validate_path()` for file operations
- Sanitize user input with `security.sanitize_user_input()`
- Handle errors using specific exceptions from `src.exceptions`
- Never log sensitive data - use `security.redact_sensitive_data()`
- Run `config.validate_configuration()` on startup
- See SECURITY.md for comprehensive security guidelines