# Multi-Agent AI Research System

A sophisticated research system that orchestrates multiple Claude AI models to conduct comprehensive research on any topic. Built with CrewAI, AWS Bedrock, and Gradio.

![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![CrewAI](https://img.shields.io/badge/CrewAI-Latest-orange.svg)
![Bedrock](https://img.shields.io/badge/AWS-Bedrock-yellow.svg)

## Overview

This system employs a hierarchical multi-agent architecture where a lead researcher (Claude Sonnet) coordinates multiple sub-researchers (Claude Haiku) working in parallel. The system includes quality control, fact-checking, and iterative refinement to ensure high-quality research output.

### Key Features

- 🤖 **Multi-Agent Orchestration**: Lead researcher coordinates 4-20 parallel sub-researchers
- 🔍 **Smart Search Integration**: Tavily API with intelligent caching
- ✅ **Quality Assurance**: Automated fact-checking and source evaluation
- 💭 **Transparent Reasoning**: Real-time thought logging and decision tracking
- 📊 **Cost Optimization**: Strategic model selection (~$0.10-0.20 per query)
- 🔄 **Iterative Refinement**: Automatic quality-based research iterations
- 💾 **Persistent Storage**: SQLite databases for research history and caching
- 🎯 **Definitive Answers**: Structured synthesis with actionable recommendations

## Architecture

View interactive diagrams: `open docs/view_architecture.html`

The system consists of:
- **Lead Researcher** (Claude Sonnet): Plans research and synthesizes findings
- **Sub-Researchers** (Claude Haiku): Conduct parallel specialized searches
- **Quality Controller**: Evaluates research completeness (75/100 threshold)
- **Source Evaluator**: Assesses credibility and relevance
- **Fact Checker**: Verifies claims and detects contradictions

## Quick Start

### Prerequisites

- Python 3.11
- AWS Account with Bedrock access
- Tavily API key
- uv package manager (`pip install uv`)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/multi-agent-research.git
cd multi-agent-research

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys:
# - TAVILY_API_KEY
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - AWS_REGION (us-east-1 or us-west-2)
```

### Running the Application

```bash
# Launch the web interface
uv run python main.py

# Open browser to http://localhost:7860
```

### Example Usage

1. Enter your research query (e.g., "What are the best practices for implementing RAG systems?")
2. Adjust the number of sub-researchers (4-20)
3. Click "Start Research"
4. Monitor progress in real-time via the thought stream
5. Review comprehensive results with clickable citations

## Features in Detail

### Intelligent Research Planning
The lead researcher analyzes queries and creates targeted research angles for comprehensive coverage.

### Parallel Processing
Multiple sub-researchers work simultaneously, each focusing on specific aspects of the query.

### Quality Control Loop
- Automatic evaluation of research completeness
- Iterative refinement if quality score < 75/100
- Maximum 3 iterations to prevent infinite loops

### Real-Time Monitoring
- Live thought stream showing AI reasoning
- Search result tracking
- Cost estimation and tracking
- Progress indicators

### Comprehensive Output
- Executive summary with concrete answers
- Detailed findings with evidence
- Actionable recommendations
- Risk assessments
- Prioritized next steps
- Clickable source citations

## Configuration

### Model Selection
Edit `config/models.yaml` to change models:
```yaml
models:
  lead_researcher:
    model_id: "us.anthropic.claude-sonnet-4-20250514-v1:0"
  sub_researcher:
    model_id: "us.anthropic.claude-3-5-haiku-20241022-v1:0"
```

### Agent Configuration
```yaml
agents:
  min_sub_researchers: 4
  max_sub_researchers: 20
  default_sub_researchers: 7
```

## Development

### Project Structure
```
multi-agent-research/
├── agents/           # Agent implementations
├── src/             # Core infrastructure
├── tools/           # External integrations
├── ui/              # Gradio interface
├── config/          # Configuration files
├── docs/            # Architecture diagrams
└── data/            # Output and logs
```

### Adding New Agents
1. Create agent class inheriting from `BaseAgent`
2. Implement thought logging
3. Integrate into `ResearchCrew`
4. Update architecture diagrams

### Debugging
- Add `[DEBUG]` to queries for detailed logs
- Monitor thought logs: `tail -f data/thought_logs/thoughts_*.jsonl | jq '.'`
- Check `search_cache.db` for cached results

## Cost Management

Typical costs per research query:
- Lead Researcher: ~$0.02-0.04
- Sub-Researchers: ~$0.06-0.12
- Quality Control: ~$0.02-0.04
- **Total: ~$0.10-0.20**

## Security

The system implements comprehensive security measures:
- Secure credential management with environment variables
- Input validation and sanitization
- Path traversal protection
- Rate limiting for API calls
- SQL injection prevention
- Thread-safe operations

See [SECURITY.md](SECURITY.md) for detailed security information.

## Recent Updates

- **2025-06-22**: Implemented comprehensive security measures
- **2025-06-22**: Fixed session selection and made citations clickable
- **2025-06-22**: Added comprehensive architecture documentation
- **2025-06-22**: Enhanced synthesis with concrete answers
- **2025-06-22**: Implemented iterative research refinement

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Update tests and documentation
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [CrewAI](https://github.com/joaomdmoura/crewAI)
- Powered by [AWS Bedrock](https://aws.amazon.com/bedrock/) and Anthropic's Claude
- Search via [Tavily API](https://tavily.com/)
- UI with [Gradio](https://gradio.app/)

## Support

For issues, questions, or contributions, please open an issue on GitHub.