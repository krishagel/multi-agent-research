"""Fact Checker agent for verifying claims and cross-referencing information."""
from typing import Dict, Any, List, Optional
from agents.base_agent import BedrockAgent
from tools.search_tool import TavilySearchTool
from src.thought_logger import ThoughtType
import re

class FactChecker(BedrockAgent):
    """Agent responsible for fact-checking claims and verifying information."""
    
    def __init__(self, verbose: bool = True, debug: bool = False):
        super().__init__(
            role="Fact Checker and Verification Specialist",
            goal="Verify claims, cross-reference information, identify contradictions, and ensure accuracy of research findings",
            backstory="""You are a meticulous fact-checker with expertise in information verification,
            source reliability assessment, and claim validation. You excel at identifying potential
            misinformation, contradictions between sources, and ensuring that all claims are
            properly supported by evidence. You maintain a skeptical but fair approach to
            information verification.""",
            agent_type="fact_checker",
            bedrock_model_config=None,  # Will use default from config
            verbose=verbose
        )
        self.search_tool = TavilySearchTool(debug=debug)
        self.debug = debug
    
    def prepare_prompt(self, task: Any) -> str:
        """Prepare a prompt for fact-checking tasks."""
        # For fact checker, we typically don't use CrewAI tasks directly
        # This method is required by base class but fact checking uses custom methods
        return str(task) if task else ""
    
    def check_facts(self, findings: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
        """Check facts across all research findings."""
        self.log_thought(
            ThoughtType.EVALUATING,
            f"Starting fact-checking process for {len(findings)} research findings",
            metadata={"num_findings": len(findings), "query": original_query}
        )
        
        # Extract all claims that need verification
        claims_to_verify = self._extract_claims(findings)
        
        self.log_thought(
            ThoughtType.INFO,
            f"Extracted {len(claims_to_verify)} claims requiring verification",
            metadata={"claims_count": len(claims_to_verify)}
        )
        
        # Verify each claim
        verification_results = []
        contradictions = []
        
        for i, claim in enumerate(claims_to_verify[:10]):  # Limit to top 10 claims
            self.log_thought(
                ThoughtType.ANALYZING,
                f"Verifying claim {i+1}/{min(len(claims_to_verify), 10)}: {claim['claim'][:100]}...",
                metadata={"claim": claim['claim'], "source": claim['source']}
            )
            
            verification = self._verify_claim(claim, original_query)
            verification_results.append(verification)
            
            # Check for contradictions
            if verification['verification_status'] == 'contradicted':
                contradictions.append(verification)
        
        # Cross-reference information between sources
        cross_references = self._cross_reference_sources(findings)
        
        # Compile fact-checking report
        report = self._compile_fact_check_report(
            verification_results,
            contradictions,
            cross_references,
            findings
        )
        
        self.log_thought(
            ThoughtType.SYNTHESIZING,
            "Completed fact-checking process",
            metadata={
                "verified_claims": len(verification_results),
                "contradictions_found": len(contradictions),
                "overall_reliability": report['overall_reliability_score']
            },
            confidence=0.9
        )
        
        return report
    
    def _extract_claims(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract specific claims that need verification."""
        claims = []
        
        for finding in findings:
            text = finding.get('findings', '')
            sources = finding.get('sources', [])
            
            # Extract claims with numbers, percentages, or definitive statements
            # Look for patterns like "X is Y", "X% of", "According to", etc.
            claim_patterns = [
                r'(\d+%?\s+of\s+[^.]+)',  # Percentages and statistics
                r'([A-Z][^.]*\s+(?:is|are|was|were|has|have)\s+[^.]+)',  # Definitive statements
                r'(According to[^,]+,[^.]+)',  # Attributed claims
                r'(Studies show[^.]+)',  # Research claims
                r'(Research indicates[^.]+)',  # Research claims
            ]
            
            for pattern in claim_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match) > 20:  # Filter out very short matches
                        claims.append({
                            'claim': match.strip(),
                            'source': finding.get('angle', 'Unknown'),
                            'original_sources': sources
                        })
        
        # Deduplicate similar claims
        unique_claims = []
        seen = set()
        for claim in claims:
            claim_key = claim['claim'].lower()[:50]
            if claim_key not in seen:
                seen.add(claim_key)
                unique_claims.append(claim)
        
        return unique_claims
    
    def _verify_claim(self, claim: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Verify a specific claim."""
        # Search for verification
        verification_query = f"verify fact check {claim['claim']}"
        search_results = self.search_tool.search(
            verification_query,
            max_results=5,
            use_cache=False  # Don't use cache for fact-checking
        )
        
        if not search_results.get('results'):
            return {
                'claim': claim['claim'],
                'verification_status': 'unverifiable',
                'confidence': 0.3,
                'evidence': [],
                'notes': 'No verification sources found'
            }
        
        # Analyze search results for verification
        verification_prompt = f"""Fact-check this claim:

CLAIM: {claim['claim']}
CONTEXT: {context}

Search results for verification:
{self.search_tool.format_results_for_llm(search_results['results'])}

Analyze whether the claim is:
1. VERIFIED - Supported by multiple credible sources
2. PARTIALLY VERIFIED - Some support but with caveats
3. CONTRADICTED - Contradicted by credible sources
4. UNVERIFIABLE - Cannot be definitively verified

Provide your assessment with evidence."""

        assessment = self.invoke_llm(verification_prompt)
        
        # Parse verification status
        status = 'unverifiable'
        if 'VERIFIED' in assessment.upper() and 'PARTIALLY' not in assessment.upper():
            status = 'verified'
        elif 'PARTIALLY VERIFIED' in assessment.upper():
            status = 'partially_verified'
        elif 'CONTRADICTED' in assessment.upper():
            status = 'contradicted'
        
        return {
            'claim': claim['claim'],
            'verification_status': status,
            'confidence': 0.8 if status == 'verified' else 0.5,
            'evidence': [result['url'] for result in search_results['results'][:3]],
            'assessment': assessment,
            'original_source': claim['source']
        }
    
    def _cross_reference_sources(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Cross-reference information between different sources."""
        cross_refs = []
        
        # Look for similar topics across findings
        for i, finding1 in enumerate(findings):
            for j, finding2 in enumerate(findings[i+1:], i+1):
                similarity = self._check_similarity(finding1, finding2)
                if similarity['is_related']:
                    cross_refs.append({
                        'source1': finding1['angle'],
                        'source2': finding2['angle'],
                        'relationship': similarity['relationship'],
                        'agreement_level': similarity['agreement_level']
                    })
        
        return cross_refs
    
    def _check_similarity(self, finding1: Dict[str, Any], finding2: Dict[str, Any]) -> Dict[str, Any]:
        """Check if two findings discuss similar topics."""
        prompt = f"""Compare these two research findings:

Finding 1 ({finding1['angle']}):
{finding1['findings'][:500]}...

Finding 2 ({finding2['angle']}):
{finding2['findings'][:500]}...

Are they discussing related topics? If yes:
1. What is the relationship?
2. Do they agree, disagree, or complement each other?
3. Rate agreement level: HIGH/MEDIUM/LOW/CONTRADICTORY

Be concise."""

        response = self.invoke_llm(prompt)
        
        # Simple parsing
        is_related = 'related' in response.lower() or 'similar' in response.lower()
        agreement = 'HIGH' if 'high' in response.upper() else 'MEDIUM'
        if 'contradict' in response.lower():
            agreement = 'CONTRADICTORY'
        
        return {
            'is_related': is_related,
            'relationship': response[:100],
            'agreement_level': agreement
        }
    
    def _compile_fact_check_report(
        self,
        verification_results: List[Dict[str, Any]],
        contradictions: List[Dict[str, Any]],
        cross_references: List[Dict[str, Any]],
        findings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Compile a comprehensive fact-checking report."""
        # Calculate reliability scores
        verified_count = sum(1 for v in verification_results if v['verification_status'] == 'verified')
        partially_verified = sum(1 for v in verification_results if v['verification_status'] == 'partially_verified')
        contradicted = len(contradictions)
        
        total_checked = len(verification_results)
        reliability_score = 0
        if total_checked > 0:
            reliability_score = (
                (verified_count * 1.0 + partially_verified * 0.5) / total_checked
            ) * 100
        
        # Identify high-confidence facts
        high_confidence_facts = [
            v for v in verification_results 
            if v['verification_status'] == 'verified' and v.get('confidence', 0) > 0.7
        ]
        
        return {
            'total_claims_checked': total_checked,
            'verified_claims': verified_count,
            'partially_verified_claims': partially_verified,
            'contradicted_claims': contradicted,
            'overall_reliability_score': reliability_score,
            'contradictions': contradictions,
            'cross_references': cross_references,
            'high_confidence_facts': high_confidence_facts,
            'verification_details': verification_results,
            'recommendations': self._generate_recommendations(
                reliability_score,
                contradictions,
                verification_results
            )
        }
    
    def _generate_recommendations(
        self,
        reliability_score: float,
        contradictions: List[Dict[str, Any]],
        verification_results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate recommendations based on fact-checking results."""
        recommendations = []
        
        if reliability_score < 70:
            recommendations.append("Consider additional research from more authoritative sources")
        
        if contradictions:
            recommendations.append("Review contradictory claims and seek clarification from primary sources")
        
        unverifiable = [v for v in verification_results if v['verification_status'] == 'unverifiable']
        if len(unverifiable) > 2:
            recommendations.append("Several claims could not be verified - treat these with caution")
        
        if reliability_score > 85:
            recommendations.append("Research findings show high reliability - proceed with confidence")
        
        return recommendations