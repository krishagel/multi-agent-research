"""Quality Controller agent that evaluates and improves research quality."""
from typing import Dict, Any, List, Tuple
from agents.base_agent import BedrockAgent
from src.thought_logger import ThoughtType
from crewai import Task

class QualityController(BedrockAgent):
    """Quality controller that evaluates research quality and guides improvements."""
    
    def __init__(self, verbose: bool = True):
        super().__init__(
            role="Research Quality Controller",
            goal="Evaluate research quality, identify gaps, and ensure findings comprehensively address user queries",
            backstory="""You are an expert research quality assessor with deep understanding of what makes research 
            thorough, accurate, and useful. You excel at identifying information gaps, evaluating source credibility, 
            and ensuring research conclusions are well-supported by evidence. You maintain high standards for 
            factual accuracy and comprehensive coverage of topics.""",
            agent_type="quality_controller",
            bedrock_model_config=None,  # Will use default from config
            verbose=verbose,
            allow_delegation=False
        )
        
    def prepare_prompt(self, task: Task) -> str:
        """Prepare a prompt for quality evaluation."""
        return task.description  # Use task description directly for evaluation prompts
    
    def evaluate_research_plan(self, plan: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Evaluate if the research plan adequately addresses the query."""
        self.log_thought(
            ThoughtType.EVALUATING,
            "Evaluating research plan quality",
            metadata={"query": query, "num_angles": len(plan.get('research_angles', []))}
        )
        
        prompt = f"""As a Research Quality Controller, evaluate this research plan:

Original Query: {query}

Research Plan:
{plan['plan']}

Research Angles:
{chr(10).join([f"{i+1}. {angle}" for i, angle in enumerate(plan['research_angles'])])}

Please evaluate:
1. Does the plan comprehensively address all aspects of the query?
2. Are the research angles specific and actionable?
3. Are there any obvious gaps or missing perspectives?
4. Will these angles likely yield high-quality, relevant information?

Provide:
- Quality Score (0-100): How well does this plan address the query?
- Specific Improvements: What research angles should be added or refined?
- Confidence Level (0-1): How confident are you in this evaluation?

Format your response as:
QUALITY_SCORE: [number]
CONFIDENCE: [number]
GAPS: [list any missing aspects]
IMPROVEMENTS: [specific suggestions]
EVALUATION: [detailed explanation]"""

        response = self.invoke_llm(prompt)
        
        # Parse response
        quality_score = self._extract_score(response, "QUALITY_SCORE")
        confidence = self._extract_score(response, "CONFIDENCE")
        
        result = {
            "quality_score": quality_score,
            "confidence": confidence,
            "gaps": self._extract_section(response, "GAPS"),
            "improvements": self._extract_section(response, "IMPROVEMENTS"),
            "evaluation": self._extract_section(response, "EVALUATION"),
            "recommendation": "proceed" if quality_score >= 70 else "refine"
        }
        
        self.log_thought(
            ThoughtType.DECIDING,
            f"Plan quality score: {quality_score}/100",
            metadata=result,
            confidence=confidence
        )
        
        return result
    
    def evaluate_search_results(self, results: List[Dict[str, Any]], query: str, angle: str) -> Dict[str, Any]:
        """Evaluate the quality and relevance of search results."""
        self.log_thought(
            ThoughtType.EVALUATING,
            f"Evaluating {len(results)} search results",
            metadata={"query": query, "angle": angle}
        )
        
        # Format results for evaluation
        results_text = "\n\n".join([
            f"Result {i+1}:\nTitle: {r.get('title', 'N/A')}\nURL: {r.get('url', 'N/A')}\nContent: {r.get('content', '')[:200]}..."
            for i, r in enumerate(results[:5])
        ])
        
        prompt = f"""Evaluate these search results for quality and relevance:

Original Query: {query}
Research Angle: {angle}

Search Results:
{results_text}

Evaluate:
1. How relevant are these results to the research angle?
2. Are the sources credible and authoritative?
3. Do the results provide substantive information?
4. Are there better search queries that would yield more relevant results?

Provide:
- RELEVANCE_SCORE: [0-100]
- CREDIBILITY_SCORE: [0-100]
- COVERAGE_SCORE: [0-100]
- SUGGESTED_QUERIES: [list better search queries if needed]
- EVALUATION: [detailed assessment]"""

        response = self.invoke_llm(prompt)
        
        return {
            "relevance_score": self._extract_score(response, "RELEVANCE_SCORE"),
            "credibility_score": self._extract_score(response, "CREDIBILITY_SCORE"),
            "coverage_score": self._extract_score(response, "COVERAGE_SCORE"),
            "suggested_queries": self._extract_section(response, "SUGGESTED_QUERIES"),
            "evaluation": self._extract_section(response, "EVALUATION"),
            "overall_quality": (self._extract_score(response, "RELEVANCE_SCORE") + 
                               self._extract_score(response, "CREDIBILITY_SCORE") + 
                               self._extract_score(response, "COVERAGE_SCORE")) / 3
        }
    
    def evaluate_findings(self, findings: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
        """Evaluate if the research findings adequately answer the original query."""
        self.log_thought(
            ThoughtType.EVALUATING,
            f"Evaluating final research findings",
            metadata={"num_findings": len(findings), "query": original_query}
        )
        
        # Format findings
        findings_text = "\n\n".join([
            f"**{f['angle']}**\n{f['findings'][:500]}..."
            for f in findings
        ])
        
        prompt = f"""Evaluate these research findings against the original query:

Original Query: {original_query}

Research Findings:
{findings_text}

Evaluate:
1. Do the findings comprehensively answer the original query?
2. Are there any aspects of the query that remain unanswered?
3. Is the information accurate and well-supported?
4. Are there contradictions between different findings?
5. What critical information is still missing?

Provide:
- COMPLETENESS_SCORE: [0-100] How completely do the findings answer the query?
- ACCURACY_SCORE: [0-100] How accurate and reliable is the information?
- CONFIDENCE: [0-1] Your confidence in this evaluation
- MISSING_INFO: [list any critical missing information]
- CONTRADICTIONS: [list any contradictions found]
- IMPROVEMENTS: [specific suggestions for additional research]
- EVALUATION: [detailed assessment]"""

        response = self.invoke_llm(prompt)
        
        completeness = self._extract_score(response, "COMPLETENESS_SCORE")
        accuracy = self._extract_score(response, "ACCURACY_SCORE")
        confidence = self._extract_score(response, "CONFIDENCE")
        
        result = {
            "completeness_score": completeness,
            "accuracy_score": accuracy,
            "confidence": confidence,
            "missing_info": self._extract_section(response, "MISSING_INFO"),
            "contradictions": self._extract_section(response, "CONTRADICTIONS"),
            "improvements": self._extract_section(response, "IMPROVEMENTS"),
            "evaluation": self._extract_section(response, "EVALUATION"),
            "overall_quality": (completeness + accuracy) / 2,
            "recommendation": "finalize" if (completeness + accuracy) / 2 >= 75 else "iterate"
        }
        
        self.log_thought(
            ThoughtType.DECIDING,
            f"Research quality: {result['overall_quality']:.1f}/100 - Recommendation: {result['recommendation']}",
            metadata={
                **result,
                "decision_rationale": f"{'Proceeding to synthesis' if result['recommendation'] == 'finalize' else 'Additional research needed'}",
                "quality_factors": {
                    "completeness": f"{completeness}% - Does research answer all aspects?",
                    "accuracy": f"{accuracy}% - Is information reliable and verified?",
                    "threshold": "75% overall quality required for finalization"
                },
                "next_steps": "Synthesize findings" if result['recommendation'] == 'finalize' else "Conduct targeted research on missing aspects"
            },
            confidence=confidence
        )
        
        return result
    
    def suggest_improvements(self, evaluation: Dict[str, Any]) -> List[str]:
        """Generate specific improvement suggestions based on evaluation."""
        self.log_thought(
            ThoughtType.PLANNING,
            "Generating improvement suggestions",
            metadata={"quality_score": evaluation.get('overall_quality', 0)}
        )
        
        improvements = []
        
        # Based on missing info
        if evaluation.get('missing_info'):
            improvements.extend([f"Research missing aspect: {info}" for info in evaluation['missing_info'].split('\n') if info.strip()])
        
        # Based on suggested queries
        if evaluation.get('suggested_queries'):
            improvements.extend([f"Try search query: {query}" for query in evaluation['suggested_queries'].split('\n') if query.strip()])
        
        # Based on improvements section
        if evaluation.get('improvements'):
            improvements.extend(evaluation['improvements'].split('\n'))
        
        return [imp.strip() for imp in improvements if imp.strip()]
    
    def _extract_score(self, text: str, marker: str) -> float:
        """Extract a numerical score from response text."""
        try:
            lines = text.split('\n')
            for line in lines:
                if marker in line:
                    # Extract number from line
                    import re
                    numbers = re.findall(r'[\d.]+', line)
                    if numbers:
                        return float(numbers[0])
        except:
            pass
        return 0.0
    
    def _extract_section(self, text: str, marker: str) -> str:
        """Extract a section of text after a marker."""
        try:
            lines = text.split('\n')
            capture = False
            result = []
            
            for line in lines:
                if marker in line:
                    capture = True
                    # Check if content is on same line
                    parts = line.split(':', 1)
                    if len(parts) > 1 and parts[1].strip():
                        result.append(parts[1].strip())
                elif capture and line.strip() and any(m in line for m in ['SCORE:', 'CONFIDENCE:', 'GAPS:', 'IMPROVEMENTS:', 'EVALUATION:', 'SUGGESTED_QUERIES:', 'MISSING_INFO:', 'CONTRADICTIONS:']):
                    # Hit next section, stop capturing
                    break
                elif capture and line.strip():
                    result.append(line.strip())
            
            return '\n'.join(result)
        except:
            return ""