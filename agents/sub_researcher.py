"""Sub-Researcher agent for specialized research tasks."""
from typing import Dict, Any, Optional, List
from agents.base_agent import BedrockAgent
from tools.search_tool import TavilySearchTool
from tools.crewai_search_tool import CrewAISearchTool
from crewai import Task
from pydantic import Field
from src.thought_logger import ThoughtType

class SubResearcher(BedrockAgent):
    """Sub-researcher that performs specialized research tasks."""
    
    # Define custom fields as Pydantic fields
    research_angle: str = Field(default="")
    search_tool: Optional[Any] = Field(default=None)
    
    def __init__(self, research_angle: str, verbose: bool = True, debug: bool = False):
        # Create tools
        crewai_search_tool = CrewAISearchTool()
        tavily_tool = TavilySearchTool(debug=debug)
        
        # Initialize parent class first
        super().__init__(
            role=f"Specialized Researcher - {research_angle[:50]}",
            goal=f"Conduct focused research on: {research_angle}",
            backstory=f"""You are a specialized researcher with deep expertise in information 
            gathering and analysis. Your current focus is on researching: {research_angle}. 
            You excel at finding relevant, credible sources and extracting key insights 
            that directly address your research angle.""",
            agent_type="sub_researcher",
            bedrock_model_config=None,  # Will use default from config
            verbose=verbose,
            tools=[crewai_search_tool]
        )
        
        # Now set instance attributes after parent initialization
        self.research_angle = research_angle
        self.search_tool = tavily_tool  # Keep direct reference for internal use
        
    def prepare_prompt(self, task: Task) -> str:
        """Prepare a prompt for focused research."""
        return f"""As a specialized researcher, conduct focused research on the following angle:

Research Angle: {self.research_angle}
Context: {task.description}

Please:
1. Search for relevant and credible information
2. Focus specifically on aspects related to your research angle
3. Evaluate the quality and relevance of sources
4. Extract key insights and findings
5. Note any gaps or areas needing further investigation

Provide a structured summary of your findings."""

    def conduct_research(self, context: str, max_searches: int = 3) -> Dict[str, Any]:
        """Conduct research on the assigned angle."""
        self.log_thought(
            ThoughtType.INFO,
            f"Starting research on angle: {self.research_angle}",
            metadata={"context": context[:200]}
        )
        
        research_task = Task(
            description=context,
            agent=self,
            expected_output=f"Comprehensive research findings on: {self.research_angle}"
        )
        
        # Perform iterative searches with context awareness
        all_findings = []
        all_queries_used = []
        search_queries = self._generate_search_queries(context)
        
        self.log_thought(
            ThoughtType.PLANNING,
            f"Generated {len(search_queries)} search queries",
            metadata={"queries": search_queries}
        )
        
        for i, query in enumerate(search_queries[:max_searches]):
            self.log_thought(
                ThoughtType.SEARCHING,
                f"Executing search {i+1}/{len(search_queries)}: {query}",
                metadata={"query": query, "search_number": i+1}
            )
            
            search_results = self.search_tool.search(query)
            all_queries_used.append(query)
            
            if search_results.get('results'):
                # Log detailed search results
                result_summaries = []
                for idx, result in enumerate(search_results['results'][:5]):  # Show top 5
                    result_summaries.append({
                        "rank": idx + 1,
                        "title": result.get('title', 'No title'),
                        "url": result.get('url', ''),
                        "snippet": result.get('content', '')[:200] + "..." if result.get('content') else '',
                        "score": result.get('score', 0),
                        "domain": result.get('domain', '')
                    })
                
                self.log_thought(
                    ThoughtType.SEARCHING,
                    f"Found {len(search_results['results'])} results for query: {query}",
                    metadata={
                        "query": query,
                        "num_results": len(search_results['results']),
                        "search_depth": search_results.get('search_depth', 'unknown'),
                        "from_cache": search_results.get('from_cache', False),
                        "results": result_summaries
                    }
                )
                
                # Analyze results with LLM
                self.log_thought(
                    ThoughtType.ANALYZING,
                    f"Analyzing {len(search_results['results'])} search results",
                    metadata={"query": query}
                )
                
                analysis = self._analyze_search_results(
                    search_results['results'],
                    context
                )
                
                # Extract source URLs and metadata
                sources = []
                for result in search_results['results'][:5]:  # Top 5 sources
                    sources.append({
                        'title': result.get('title', ''),
                        'url': result.get('url', ''),
                        'domain': result.get('domain', ''),
                        'score': result.get('score', 0)
                    })
                
                all_findings.append({
                    'query': query,
                    'analysis': analysis,
                    'num_results': len(search_results['results']),
                    'sources': sources
                })
                
                self.log_thought(
                    ThoughtType.ANALYZING,
                    "Completed analysis of search results",
                    metadata={"analysis_length": len(analysis)}
                )
            else:
                # Check if there was an error
                error_msg = search_results.get('error', 'No results returned')
                self.log_thought(
                    ThoughtType.ERROR if 'error' in search_results else ThoughtType.INFO,
                    f"Search failed for query: {query}",
                    metadata={
                        "query": query,
                        "error": error_msg,
                        "search_count": search_results.get('search_count', 0),
                        "cache_hits": search_results.get('cache_hits', 0)
                    }
                )
        
        # If we have very few findings, generate additional context-aware queries
        if len(all_findings) < 2 and max_searches > len(all_queries_used):
            self.log_thought(
                ThoughtType.PLANNING,
                "Insufficient findings. Generating additional context-aware queries.",
                metadata={"current_findings": len(all_findings), "adaptive_search": True}
            )
            
            # Generate new queries based on what we've learned so far
            findings_context = "\n".join([f['analysis'][:200] + "..." for f in all_findings]) if all_findings else "No findings yet"
            additional_queries = self._generate_search_queries(
                context + "\n\nPrevious findings summary:\n" + findings_context,
                previous_queries=all_queries_used
            )
            
            # Execute additional searches
            for query in additional_queries[:max_searches - len(all_queries_used)]:
                self.log_thought(
                    ThoughtType.SEARCHING,
                    f"Executing adaptive search: {query}",
                    metadata={"query": query, "adaptive": True}
                )
                
                search_results = self.search_tool.search(query)
                all_queries_used.append(query)
                
                if search_results.get('results'):
                    analysis = self._analyze_search_results(
                        search_results['results'],
                        context + "\nRefinement needed based on initial findings."
                    )
                    
                    # Extract sources
                    sources = []
                    for result in search_results['results'][:5]:
                        sources.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'domain': result.get('domain', ''),
                            'score': result.get('score', 0)
                        })
                    
                    all_findings.append({
                        'query': query,
                        'analysis': analysis,
                        'num_results': len(search_results['results']),
                        'sources': sources
                    })
        
        # Synthesize all findings
        self.log_thought(
            ThoughtType.SYNTHESIZING,
            f"Synthesizing findings from {len(all_findings)} searches",
            metadata={
                "num_findings": len(all_findings),
                "total_queries": len(all_queries_used),
                "adaptive_searches": len(all_queries_used) - len(search_queries)
            }
        )
        
        final_synthesis = self._synthesize_research(all_findings)
        
        self.log_thought(
            ThoughtType.INFO,
            f"Completed research on angle: {self.research_angle}",
            metadata={
                "searches_performed": len(all_findings),
                "synthesis_length": len(final_synthesis),
                "total_cost": self.total_cost
            },
            confidence=0.85
        )
        
        # Collect all sources used
        all_sources = []
        for finding in all_findings:
            all_sources.extend(finding.get('sources', []))
        
        # Deduplicate sources by URL
        unique_sources = {}
        for source in all_sources:
            url = source.get('url', '')
            if url and (url not in unique_sources or source.get('score', 0) > unique_sources.get(url, {}).get('score', 0)):
                unique_sources[url] = source
        
        return {
            'angle': self.research_angle,
            'findings': final_synthesis,
            'searches_performed': len(all_findings),
            'total_cost': self.total_cost,
            'sources': list(unique_sources.values()),
            'query_details': all_findings  # Include detailed findings with sources
        }
    
    def _generate_search_queries(self, context: str, previous_queries: List[str] = None) -> List[str]:
        """Generate search queries for the research angle with context awareness."""
        self.log_thought(
            ThoughtType.PLANNING,
            f"Generating context-aware search queries for angle: {self.research_angle}",
            metadata={
                "context_preview": context[:100],
                "previous_queries": previous_queries or [],
                "strategy": "Adaptive query generation based on context and previous searches"
            }
        )
        
        previous_context = ""
        if previous_queries:
            previous_context = f"\nPrevious queries used: {', '.join(previous_queries)}"
            previous_context += "\nAvoid duplicating these queries. Instead, explore complementary aspects."
        
        prompt = f"""Given this research angle: {self.research_angle}
And this context: {context}{previous_context}

Generate 3 specific search queries that would help gather relevant information.
Consider:
1. What aspects haven't been explored yet?
2. What follow-up questions emerge from the context?
3. What alternative perspectives should be investigated?

Return only the queries, one per line. Make queries specific and diverse."""
        
        response = self.invoke_llm(prompt, log_prompt=False)  # Don't double-log
        # Clean up queries - remove quotes and extra formatting
        queries = []
        for line in response.split('\n'):
            query = line.strip()
            # Remove leading numbers, dashes, quotes
            query = query.lstrip('0123456789.-•').strip()
            query = query.strip('"\'')  # Remove quotes
            if query and len(query) > 5:  # Filter out empty or very short queries
                queries.append(query)
        
        self.log_thought(
            ThoughtType.DECIDING,
            f"Selected {len(queries)} search queries for research angle",
            metadata={
                "queries": queries,
                "decision_rationale": f"Queries designed to explore different facets of: {self.research_angle}",
                "query_strategy": [
                    "Broad initial query for overview",
                    "Specific queries for detailed information",
                    "Alternative phrasing to find diverse sources"
                ],
                "optimization": "Removed quotes and cleaned formatting to improve search results"
            },
            confidence=0.75
        )
        
        return queries[:3]  # Ensure we don't exceed limit
    
    def _analyze_search_results(self, results: List[Dict[str, Any]], context: str) -> str:
        """Analyze search results in the context of the research angle."""
        formatted_results = self.search_tool.format_results_for_llm(results[:3])
        
        prompt = f"""Analyze these search results in the context of the research angle:

Research Angle: {self.research_angle}
Context: {context}

Search Results:
{formatted_results}

Extract and summarize the key findings that are relevant to the research angle.
Focus on factual information and credible insights.

IMPORTANT: When you reference specific facts or findings, indicate which source it came from by mentioning the source number (e.g., "According to source 1..." or "As reported in source 2...")."""
        
        return self.invoke_llm(prompt)
    
    def _synthesize_research(self, findings: List[Dict[str, Any]]) -> str:
        """Synthesize all research findings."""
        findings_text = "\n\n".join([
            f"Search {i+1} ({f['query']}):\n{f['analysis']}"
            for i, f in enumerate(findings)
        ])
        
        prompt = f"""Synthesize these research findings into a comprehensive summary:

Research Angle: {self.research_angle}

Findings:
{findings_text}

Create a cohesive summary that:
1. Integrates insights from all searches
2. Highlights the most important findings
3. Notes any conflicting information or gaps
4. Provides specific examples or evidence where available"""
        
        return self.invoke_llm(prompt)