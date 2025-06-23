"""Lead Researcher agent that coordinates the research process."""
from typing import List, Dict, Any
from agents.base_agent import BedrockAgent
from crewai import Task
from src.thought_logger import ThoughtType
import re

class LeadResearcher(BedrockAgent):
    """Lead researcher that plans and coordinates research efforts."""
    
    def __init__(self, verbose: bool = True):
        super().__init__(
            role="Lead Research Coordinator",
            goal="Analyze research queries, develop comprehensive research strategies, and synthesize findings from sub-researchers into coherent, well-structured reports",
            backstory="""You are an experienced research coordinator with expertise in breaking down 
            complex queries into manageable research tasks. You excel at identifying key aspects 
            that need investigation, delegating specialized tasks to sub-researchers, and 
            synthesizing diverse findings into comprehensive insights. You ensure research is 
            thorough, accurate, and addresses all aspects of the user's query.""",
            agent_type="lead_researcher",
            bedrock_model_config=None,  # Will use default from config
            verbose=verbose,
            allow_delegation=True
        )
        
    def prepare_prompt(self, task: Task) -> str:
        """Prepare a prompt for research planning."""
        return f"""As the Lead Research Coordinator, analyze this research query and develop a comprehensive research strategy:

Query: {task.description}

Please:
1. Identify the key aspects and sub-questions that need investigation
2. Determine what types of information would be most valuable
3. Suggest 3-5 specific research angles for sub-researchers to explore
4. Consider potential challenges or areas requiring special attention

Provide a structured research plan."""

    def create_research_plan(self, query: str) -> Dict[str, Any]:
        """Create a detailed research plan for the given query."""
        self.log_thought(
            ThoughtType.PLANNING,
            f"Starting research planning for query: {query}",
            metadata={"query": query}
        )
        
        planning_task = Task(
            description=query,
            agent=self,
            expected_output="A structured research plan with key aspects and research angles"
        )
        
        # Log the planning process
        self.log_thought(
            ThoughtType.PLANNING,
            "Analyzing query to identify key research areas and angles",
            metadata={"query_length": len(query), "query_preview": query[:100]}
        )
        
        # Get research plan from the agent
        prompt = self.prepare_prompt(planning_task)
        
        self.log_thought(
            ThoughtType.PLANNING,
            "Generated research planning prompt",
            metadata={"prompt_length": len(prompt)}
        )
        
        response = self.invoke_llm(prompt)
        
        self.log_thought(
            ThoughtType.PLANNING,
            "Received research plan from LLM, parsing research angles",
            metadata={"plan_length": len(response)}
        )
        
        # Parse the response to extract research angles
        research_angles = self._parse_research_angles(response)
        
        # Log decision transparency
        self.log_thought(
            ThoughtType.DECIDING,
            f"Identified {len(research_angles)} research angles based on query analysis",
            metadata={
                "angles": research_angles,
                "decision_rationale": "Selected angles cover different aspects of the query to ensure comprehensive coverage",
                "selection_criteria": [
                    "Relevance to main query",
                    "Potential for unique insights",
                    "Coverage of different perspectives",
                    "Feasibility for search-based research"
                ]
            },
            confidence=0.8
        )
        
        return {
            'query': query,
            'plan': response,
            'research_angles': research_angles,
            'num_sub_researchers': len(research_angles)
        }
    
    def synthesize_findings(self, findings: List[Dict[str, Any]], original_query: str = "") -> str:
        """Synthesize findings from multiple sub-researchers."""
        self.log_thought(
            ThoughtType.SYNTHESIZING,
            f"Starting synthesis of findings from {len(findings)} sub-researchers",
            metadata={"num_findings": len(findings), "total_length": sum(len(f.get('findings', '')) for f in findings)}
        )
        
        synthesis_prompt, all_sources = self._create_synthesis_prompt(findings, original_query)
        
        self.log_thought(
            ThoughtType.SYNTHESIZING,
            "Generated synthesis prompt, combining all research findings",
            metadata={"prompt_length": len(synthesis_prompt)}
        )
        
        synthesis = self.invoke_llm(synthesis_prompt)
        
        # Replace inline citations with clickable links
        try:
            for i, source in enumerate(all_sources):
                citation_pattern = f"\\[{i+1}\\]"
                source_url = source.get('url', '#')
                citation_link = f"[[{i+1}]]({source_url})"
                synthesis = re.sub(citation_pattern, citation_link, synthesis)
        except Exception as e:
            self.log_thought(
                ThoughtType.ERROR,
                f"Error making citations clickable: {str(e)}",
                metadata={"error": str(e)}
            )
        
        self.log_thought(
            ThoughtType.SYNTHESIZING,
            "Completed synthesis of research findings",
            metadata={"synthesis_length": len(synthesis)},
            confidence=0.9
        )
        
        return synthesis
    
    def _parse_research_angles(self, plan: str) -> List[str]:
        """Extract specific research angles from the plan."""
        # Simple parsing - in production, use more sophisticated NLP
        angles = []
        lines = plan.split('\n')
        
        for line in lines:
            # Look for numbered items or bullet points
            if any(line.strip().startswith(marker) for marker in ['1.', '2.', '3.', '4.', '5.', '-', '•']):
                angle = line.strip().lstrip('1234567890.-•').strip()
                if len(angle) > 10:  # Filter out very short items
                    angles.append(angle)
        
        # Limit to 5 angles
        return angles[:5] if angles else [
            "General background and context",
            "Current state and recent developments",
            "Key challenges and considerations",
            "Future implications and trends"
        ]
    
    def _create_synthesis_prompt(self, findings: List[Dict[str, Any]], original_query: str) -> tuple[str, List[Dict[str, Any]]]:
        """Create a prompt for synthesizing research findings and return sources."""
        # Include sources with each finding
        findings_with_sources = []
        all_sources = []
        
        for i, f in enumerate(findings):
            sources_text = ""
            if 'sources' in f and f['sources']:
                sources_text = "\n\n**Sources Used:**\n"
                for j, source in enumerate(f['sources'][:5]):  # Top 5 sources per angle
                    source_idx = len(all_sources) + j + 1
                    sources_text += f"[{source_idx}] {source.get('title', 'Untitled')} - {source.get('domain', '')} (Relevance: {source.get('score', 0):.2f})\n"
                    all_sources.append(source)
            
            findings_with_sources.append(
                f"**Research Angle {i+1}: {f['angle']}**\n{f['findings']}{sources_text}"
            )
        
        findings_text = "\n\n".join(findings_with_sources)
        
        # Create a master source list with clickable links
        source_list = "\n".join([
            f"[{i+1}] [{s.get('title', 'Untitled')}]({s.get('url', '#')}) - {s.get('domain', '')}"
            for i, s in enumerate(all_sources)
        ])
        
        synthesis_prompt = f"""As the Lead Research Coordinator, synthesize these research findings into a comprehensive report with CONCRETE ANSWERS:

ORIGINAL QUERY: {original_query}

{findings_text}

CRITICAL REQUIREMENTS:

Create a synthesis with the following MANDATORY sections:

## EXECUTIVE SUMMARY (3-5 bullet points)
- Start each bullet with a DEFINITIVE answer or recommendation
- Include specific numbers, percentages, or concrete details
- Provide enough context to understand the significance
- Each bullet should be 2-3 sentences for clarity

## KEY FINDINGS (Numbered list with detail)
1. [Most important concrete finding]
   - Supporting evidence and context
   - Why this matters
   - Relevant data points or examples
2. [Second most important finding]
   - Supporting evidence and context
   - Implications and significance
   - Specific examples or cases
[Continue for all major findings...]

## SPECIFIC RECOMMENDATIONS
For each major aspect of the query, provide:
- WHAT to do (specific action with implementation details)
- WHY (detailed reasoning based on research evidence)
- HOW (practical steps to implement)
- CONFIDENCE LEVEL (High/Medium/Low with justification)

## DIRECT ANSWERS
Address each part of the original query with:
- A clear YES/NO or specific answer (1-2 sentences)
- Detailed explanation with supporting evidence (3-4 sentences)
- Important caveats, conditions, or exceptions
- Alternative perspectives if relevant

## EVIDENCE & SOURCES
- List the strongest pieces of evidence supporting each recommendation
- Cite specific sources using [#] notation from the source list below
- Explain why each piece of evidence is credible and relevant
- Note any conflicting information found and how you reconciled it
- Identify gaps where definitive answers weren't possible

MASTER SOURCE LIST:
{source_list}

## RISK ASSESSMENT
- Major risks if recommendations are followed
- Major risks if recommendations are NOT followed

## NEXT STEPS (Prioritized action plan)
1. Immediate actions (within 1 week)
2. Short-term actions (within 1 month)  
3. Long-term considerations

Remember: The user needs CONCRETE, ACTIONABLE ANSWERS with SUFFICIENT DETAIL to understand and implement them. 
- Be specific and definitive in your conclusions
- Provide enough context and explanation to make the answers useful
- Balance brevity with completeness - aim for clarity over terseness
- If you cannot provide a definitive answer, explain exactly what additional information would be needed and why"""
        
        return synthesis_prompt, all_sources