"""Research Crew that coordinates multiple agents."""
import asyncio
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.lead_researcher import LeadResearcher
from agents.sub_researcher import SubResearcher
from agents.quality_controller import QualityController
from agents.source_evaluator import SourceEvaluator
from agents.fact_checker import FactChecker
from src.config import config
from src.thought_logger import thought_logger, ThoughtType
from src.research_database import research_db
import json
from datetime import datetime
from pathlib import Path

class ResearchCrew:
    """Coordinates the multi-agent research system."""
    
    def __init__(self, num_sub_researchers: Optional[int] = None, debug: bool = False, enable_quality_control: bool = True):
        self.lead_researcher = LeadResearcher()
        self.quality_controller = QualityController() if enable_quality_control else None
        self.source_evaluator = SourceEvaluator() if enable_quality_control else None
        self.fact_checker = FactChecker(debug=debug) if enable_quality_control else None
        self.num_sub_researchers = num_sub_researchers or config.get_agent_config().default_sub_researchers
        self.sub_researchers = []
        self.research_history = []
        self.debug = debug
        self.enable_quality_control = enable_quality_control
        
        # Create output directory
        self.output_dir = Path("data/research_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def conduct_research(
        self,
        query: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Conduct comprehensive research on a query.
        
        Args:
            query: The research query
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict containing the research results and metadata
        """
        start_time = datetime.now()
        
        # Step 1: Lead researcher creates research plan
        if progress_callback:
            progress_callback("Creating research plan...", 0.1)
            
        research_plan = self.lead_researcher.create_research_plan(query)
        
        # Create database session
        session_id = research_db.create_session(query, research_plan)
        
        # Step 1b: Quality control evaluates the plan
        if self.enable_quality_control and self.quality_controller:
            plan_evaluation = self.quality_controller.evaluate_research_plan(research_plan, query)
            
            if plan_evaluation['quality_score'] < 70:
                thought_logger.log_thought(
                    agent_id="research_crew",
                    agent_type="orchestrator",
                    thought_type=ThoughtType.DECIDING,
                    content=f"Research plan quality score: {plan_evaluation['quality_score']}/100. Refining plan...",
                    metadata=plan_evaluation
                )
                # TODO: Implement plan refinement based on feedback
                # For now, log the suggestions
                for improvement in plan_evaluation.get('improvements', '').split('\n'):
                    if improvement.strip():
                        thought_logger.log_thought(
                            agent_id="research_crew",
                            agent_type="orchestrator",
                            thought_type=ThoughtType.INFO,
                            content=f"Suggested improvement: {improvement}"
                        )
        
        research_angles = research_plan['research_angles'][:self.num_sub_researchers]
        
        # Step 2: Create sub-researchers for each angle
        if progress_callback:
            progress_callback(f"Deploying {len(research_angles)} sub-researchers...", 0.2)
            
        self.sub_researchers = [
            SubResearcher(angle, verbose=False, debug=self.debug)
            for angle in research_angles
        ]
        
        # Step 3: Conduct parallel research
        if progress_callback:
            progress_callback("Conducting parallel research...", 0.3)
            
        findings = self._conduct_parallel_research(query, session_id, progress_callback)
        
        # Step 3b: Iterative research loop with quality control
        iteration = 1
        max_iterations = 3
        quality_threshold = 75
        
        while iteration <= max_iterations:
            if self.enable_quality_control and self.quality_controller:
                findings_evaluation = self.quality_controller.evaluate_findings(findings, query)
                
                thought_logger.log_thought(
                    agent_id="research_crew",
                    agent_type="orchestrator",
                    thought_type=ThoughtType.EVALUATING,
                    content=f"Iteration {iteration}: Research quality score: {findings_evaluation['overall_quality']:.1f}/100",
                    metadata={
                        "iteration": iteration,
                        "quality_score": findings_evaluation['overall_quality'],
                        "missing_aspects": findings_evaluation.get('missing_aspects', []),
                        "improvements": findings_evaluation.get('improvements', '')
                    }
                )
                
                if findings_evaluation['overall_quality'] >= quality_threshold:
                    thought_logger.log_thought(
                        agent_id="research_crew",
                        agent_type="orchestrator",
                        thought_type=ThoughtType.DECIDING,
                        content=f"Research quality meets threshold. Proceeding to synthesis.",
                        confidence=0.9
                    )
                    break
                
                if iteration < max_iterations:
                    # Extract missing aspects and create targeted research angles
                    missing_aspects = findings_evaluation.get('missing_aspects', [])
                    improvements = findings_evaluation.get('improvements', '')
                    
                    thought_logger.log_thought(
                        agent_id="research_crew",
                        agent_type="orchestrator",
                        thought_type=ThoughtType.PLANNING,
                        content=f"Quality below threshold. Initiating iteration {iteration + 1} with targeted research.",
                        metadata={
                            "missing_aspects": missing_aspects,
                            "improvements_needed": improvements
                        }
                    )
                    
                    if progress_callback:
                        progress_callback(f"Refining research (iteration {iteration + 1})...", 0.3 + (0.4 * iteration / max_iterations))
                    
                    # Create targeted sub-researchers for missing aspects
                    targeted_findings = self._conduct_targeted_research(
                        query, 
                        missing_aspects, 
                        improvements,
                        session_id,
                        progress_callback
                    )
                    
                    # Merge new findings with existing ones
                    findings.extend(targeted_findings)
                    
                    iteration += 1
                else:
                    thought_logger.log_thought(
                        agent_id="research_crew",
                        agent_type="orchestrator",
                        thought_type=ThoughtType.INFO,
                        content=f"Maximum iterations reached. Proceeding with current findings (quality: {findings_evaluation['overall_quality']:.1f}/100)",
                        metadata={"final_quality": findings_evaluation['overall_quality']}
                    )
                    break
            else:
                # No quality control enabled, proceed directly
                break
        
        # Step 3c: Fact-checking (after iterative research completes)
        if self.enable_quality_control and self.fact_checker:
            if progress_callback:
                progress_callback("Fact-checking research findings...", 0.75)
            
            fact_check_report = self.fact_checker.check_facts(findings, query)
            
            thought_logger.log_thought(
                agent_id="research_crew",
                agent_type="orchestrator",
                thought_type=ThoughtType.EVALUATING,
                content=f"Fact-checking complete. Reliability score: {fact_check_report['overall_reliability_score']:.1f}%",
                metadata={
                    "verified_claims": fact_check_report['verified_claims'],
                    "contradictions": len(fact_check_report['contradictions']),
                    "recommendations": fact_check_report['recommendations']
                }
            )
            
            # Add fact-check report to findings for synthesis
            findings.append({
                'angle': 'Fact-Checking and Verification Report',
                'findings': self._format_fact_check_report(fact_check_report),
                'searches_performed': 0,
                'total_cost': self.fact_checker.total_cost,
                'sources': []
            })
        
        # Step 4: Synthesize findings
        if progress_callback:
            progress_callback("Synthesizing research findings...", 0.8)
            
        final_synthesis = self.lead_researcher.synthesize_findings(findings, query)
        
        # Step 5: Compile results
        if progress_callback:
            progress_callback("Compiling final report...", 0.9)
            
        research_result = self._compile_results(
            query, research_plan, findings, final_synthesis, start_time
        )
        
        # Save results to files
        self._save_research(research_result)
        
        # Complete session in database
        duration = (datetime.now() - start_time).total_seconds()
        total_cost = self.lead_researcher.total_cost + sum(r.total_cost for r in self.sub_researchers)
        if self.fact_checker:
            total_cost += self.fact_checker.total_cost
        total_searches = sum(r.search_tool.search_count for r in self.sub_researchers)
        
        research_db.complete_session(
            session_id=session_id,
            synthesis=final_synthesis,
            duration_seconds=duration,
            total_cost=total_cost,
            total_searches=total_searches
        )
        
        # Add session_id to result
        research_result['session_id'] = session_id
        
        if progress_callback:
            progress_callback("Research complete!", 1.0)
            
        return research_result
    
    def _conduct_parallel_research(
        self,
        query: str,
        session_id: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Conduct research in parallel using sub-researchers."""
        findings = []
        
        with ThreadPoolExecutor(max_workers=self.num_sub_researchers) as executor:
            # Submit all research tasks
            future_to_researcher = {
                executor.submit(researcher.conduct_research, query): researcher
                for researcher in self.sub_researchers
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_researcher):
                researcher = future_to_researcher[future]
                try:
                    result = future.result()
                    findings.append(result)
                    completed += 1
                    
                    # Save finding to database
                    research_db.save_finding(
                        session_id=session_id,
                        research_angle=result['angle'],
                        findings=result['findings'],
                        searches_performed=result['searches_performed'],
                        cost=result['total_cost'],
                        sources=result.get('sources', []),
                        query_details=result.get('query_details', [])
                    )
                    
                    if progress_callback:
                        progress = 0.3 + (0.5 * completed / len(self.sub_researchers))
                        progress_callback(
                            f"Completed research angle {completed}/{len(self.sub_researchers)}",
                            progress
                        )
                        
                except Exception as e:
                    findings.append({
                        'angle': researcher.research_angle,
                        'findings': f"Error during research: {str(e)}",
                        'error': True
                    })
        
        return findings
    
    def _conduct_targeted_research(
        self,
        query: str,
        missing_aspects: List[str],
        improvements: str,
        session_id: str,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Conduct targeted research on specific missing aspects."""
        targeted_angles = []
        
        # Create targeted research angles from missing aspects
        if missing_aspects:
            for aspect in missing_aspects[:2]:  # Limit to 2 targeted researchers
                targeted_angles.append(f"Specific investigation: {aspect}")
        
        # If no specific aspects, create a general improvement angle
        if not targeted_angles and improvements:
            targeted_angles.append(f"Additional research based on: {improvements[:100]}...")
        
        if not targeted_angles:
            return []
        
        thought_logger.log_thought(
            agent_id="research_crew",
            agent_type="orchestrator",
            thought_type=ThoughtType.PLANNING,
            content=f"Creating {len(targeted_angles)} targeted researchers",
            metadata={"targeted_angles": targeted_angles}
        )
        
        # Create targeted sub-researchers
        targeted_researchers = [
            SubResearcher(angle, verbose=False, debug=self.debug)
            for angle in targeted_angles
        ]
        
        # Conduct targeted research
        targeted_findings = []
        with ThreadPoolExecutor(max_workers=len(targeted_researchers)) as executor:
            future_to_researcher = {
                executor.submit(researcher.conduct_research, query): researcher
                for researcher in targeted_researchers
            }
            
            for future in as_completed(future_to_researcher):
                researcher = future_to_researcher[future]
                try:
                    result = future.result()
                    targeted_findings.append(result)
                    
                    # Save to database
                    research_db.save_finding(
                        session_id=session_id,
                        research_angle=result['angle'],
                        findings=result['findings'],
                        searches_performed=result['searches_performed'],
                        cost=result['total_cost'],
                        sources=result.get('sources', []),
                        query_details=result.get('query_details', [])
                    )
                    
                except Exception as e:
                    thought_logger.log_thought(
                        agent_id="research_crew",
                        agent_type="orchestrator",
                        thought_type=ThoughtType.ERROR,
                        content=f"Targeted research failed: {str(e)}",
                        metadata={"error": str(e), "researcher": researcher.research_angle}
                    )
        
        return targeted_findings
    
    def _compile_results(
        self,
        query: str,
        research_plan: Dict[str, Any],
        findings: List[Dict[str, Any]],
        synthesis: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Compile all research results into a structured format."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate total costs
        total_cost = self.lead_researcher.total_cost
        for researcher in self.sub_researchers:
            total_cost += researcher.total_cost
        
        # Get search statistics
        total_searches = sum(
            researcher.search_tool.search_count
            for researcher in self.sub_researchers
        )
        
        return {
            'query': query,
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'research_plan': research_plan['plan'],
            'research_angles': research_plan['research_angles'],
            'findings': findings,
            'synthesis': synthesis,
            'statistics': {
                'num_researchers': len(self.sub_researchers) + 1,
                'total_searches': total_searches,
                'total_cost': total_cost,
                'lead_researcher_cost': self.lead_researcher.total_cost,
                'avg_sub_researcher_cost': total_cost / max(1, len(self.sub_researchers))
            }
        }
    
    def _save_research(self, research_result: Dict[str, Any]):
        """Save research results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(research_result, f, indent=2)
        
        # Also save a markdown version
        markdown_filename = f"research_{timestamp}.md"
        markdown_filepath = self.output_dir / markdown_filename
        
        with open(markdown_filepath, 'w') as f:
            f.write(self._format_as_markdown(research_result))
        
        # Update history
        self.research_history.append({
            'timestamp': research_result['timestamp'],
            'query': research_result['query'],
            'filepath': str(filepath),
            'markdown_filepath': str(markdown_filepath),
            'cost': research_result['statistics']['total_cost']
        })
    
    def _format_as_markdown(self, research_result: Dict[str, Any]) -> str:
        """Format research results as markdown."""
        md = f"""# Research Report

**Query:** {research_result['query']}  
**Date:** {research_result['timestamp']}  
**Duration:** {research_result['duration_seconds']:.1f} seconds  
**Total Cost:** ${research_result['statistics']['total_cost']:.4f}

## Research Plan

{research_result['research_plan']}

## Research Findings

"""
        
        for finding in research_result['findings']:
            md += f"### {finding['angle']}\n\n"
            md += f"{finding['findings']}\n\n"
        
        md += f"""## Synthesis

{research_result['synthesis']}

## Statistics

- Number of Researchers: {research_result['statistics']['num_researchers']}
- Total Searches: {research_result['statistics']['total_searches']}
- Total Cost: ${research_result['statistics']['total_cost']:.4f}
- Lead Researcher Cost: ${research_result['statistics']['lead_researcher_cost']:.4f}
"""
        
        return md
    
    def _format_fact_check_report(self, report: Dict[str, Any]) -> str:
        """Format fact-check report for inclusion in findings."""
        formatted = f"""## Fact-Checking Results

**Overall Reliability Score:** {report['overall_reliability_score']:.1f}%

### Verification Summary
- Total Claims Checked: {report['total_claims_checked']}
- Verified Claims: {report['verified_claims']}
- Partially Verified: {report['partially_verified_claims']}
- Contradicted Claims: {report['contradicted_claims']}

### Key Findings
"""
        
        # Add high-confidence facts
        if report['high_confidence_facts']:
            formatted += "\n**High Confidence Facts:**\n"
            for fact in report['high_confidence_facts'][:5]:
                formatted += f"- ✓ {fact['claim']}\n"
        
        # Add contradictions
        if report['contradictions']:
            formatted += "\n**⚠️ Contradictions Found:**\n"
            for contradiction in report['contradictions'][:3]:
                formatted += f"- {contradiction['claim']}\n"
                formatted += f"  Assessment: {contradiction['assessment'][:100]}...\n"
        
        # Add recommendations
        if report['recommendations']:
            formatted += "\n### Recommendations\n"
            for rec in report['recommendations']:
                formatted += f"- {rec}\n"
        
        return formatted
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            'total_researches': len(self.research_history),
            'total_cost': sum(r['cost'] for r in self.research_history),
            'lead_researcher_stats': self.lead_researcher.get_usage_stats(),
            'recent_researches': self.research_history[-5:]
        }