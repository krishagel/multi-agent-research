"""Source Evaluator agent that assesses credibility and relevance of sources."""
from typing import Dict, Any, List, Optional, ClassVar, Set
from agents.base_agent import BedrockAgent
from src.thought_logger import ThoughtType
from crewai import Task
from datetime import datetime
from urllib.parse import urlparse

class SourceEvaluator(BedrockAgent):
    """Source evaluator that assesses credibility and relevance of information sources."""
    
    # Known high-quality domains
    AUTHORITATIVE_DOMAINS: ClassVar[Set[str]] = {
        # Academic
        'arxiv.org', 'nature.com', 'science.org', 'ieee.org', 'acm.org',
        'springer.com', 'wiley.com', 'nih.gov', 'ncbi.nlm.nih.gov', 'jstor.org',
        
        # News and journalism
        'reuters.com', 'apnews.com', 'bbc.com', 'npr.org', 'wsj.com',
        'nytimes.com', 'washingtonpost.com', 'ft.com', 'economist.com',
        
        # Tech and industry
        'github.com', 'stackoverflow.com', 'docs.microsoft.com', 'developer.mozilla.org',
        'cloud.google.com', 'aws.amazon.com', 'openai.com', 'anthropic.com',
        
        # Government and institutions
        'gov', 'edu', 'ac.uk', 'org',  # TLDs
        'un.org', 'who.int', 'worldbank.org', 'imf.org'
    }
    
    # Potentially biased or less reliable domains
    CAUTION_DOMAINS: ClassVar[Set[str]] = {
        'medium.com', 'quora.com', 'reddit.com', 'facebook.com', 
        'linkedin.com', 'twitter.com', 'x.com', 'tiktok.com'
    }
    
    def __init__(self, verbose: bool = True):
        super().__init__(
            role="Source Credibility Evaluator",
            goal="Assess the credibility, authority, and relevance of information sources",
            backstory="""You are an expert in evaluating information sources with deep knowledge of 
            academic standards, journalistic integrity, and domain expertise. You can quickly assess 
            whether a source is credible, identify potential biases, and determine the authority 
            of authors and publications. You understand the importance of primary sources and 
            can distinguish between peer-reviewed research, journalism, and opinion pieces.""",
            agent_type="source_evaluator",
            bedrock_model_config=None,
            verbose=verbose,
            allow_delegation=False
        )
        
    def prepare_prompt(self, task: Task) -> str:
        """Prepare a prompt for source evaluation."""
        return task.description
    
    def evaluate_source(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single source for credibility and relevance."""
        url = source.get('url', '')
        domain = source.get('domain', self._extract_domain(url))
        title = source.get('title', '')
        content = source.get('content', '')
        published_date = source.get('published_date', '')
        
        self.log_thought(
            ThoughtType.EVALUATING,
            f"Evaluating source: {domain}",
            metadata={"url": url, "title": title}
        )
        
        # Quick domain-based scoring
        domain_score = self._score_domain(domain)
        
        # Evaluate content and metadata
        prompt = f"""Evaluate this source for credibility and quality:

URL: {url}
Domain: {domain}
Title: {title}
Published Date: {published_date}
Content Preview: {content[:500]}...

Please assess:
1. Source Authority: Is this a reputable publication/website?
2. Content Quality: Is the information well-researched and factual?
3. Bias Detection: Are there signs of bias or opinion vs. fact?
4. Currency: Is the information current and relevant?
5. Primary vs Secondary: Is this a primary source or secondary reporting?

Provide scores (0-100) for:
- AUTHORITY_SCORE: Domain and publication credibility
- QUALITY_SCORE: Content quality and accuracy
- OBJECTIVITY_SCORE: Freedom from bias
- CURRENCY_SCORE: Timeliness and relevance
- OVERALL_CREDIBILITY: Combined assessment

Also provide:
- SOURCE_TYPE: [academic/news/blog/social/government/commercial]
- BIAS_INDICATORS: Any detected bias
- WARNINGS: Any credibility concerns
- EVALUATION: Brief assessment"""

        response = self.invoke_llm(prompt)
        
        # Parse scores
        authority = self._extract_score(response, "AUTHORITY_SCORE")
        quality = self._extract_score(response, "QUALITY_SCORE")
        objectivity = self._extract_score(response, "OBJECTIVITY_SCORE")
        currency = self._extract_score(response, "CURRENCY_SCORE")
        overall = self._extract_score(response, "OVERALL_CREDIBILITY")
        
        # Adjust scores based on domain knowledge
        if domain_score >= 80:
            authority = max(authority, domain_score)
        elif domain_score <= 30:
            authority = min(authority, domain_score)
            
        result = {
            "url": url,
            "domain": domain,
            "domain_score": domain_score,
            "authority_score": authority,
            "quality_score": quality,
            "objectivity_score": objectivity,
            "currency_score": currency,
            "overall_credibility": overall or (authority + quality + objectivity + currency) / 4,
            "source_type": self._extract_section(response, "SOURCE_TYPE"),
            "bias_indicators": self._extract_section(response, "BIAS_INDICATORS"),
            "warnings": self._extract_section(response, "WARNINGS"),
            "evaluation": self._extract_section(response, "EVALUATION")
        }
        
        self.log_thought(
            ThoughtType.DECIDING,
            f"Source credibility: {result['overall_credibility']:.1f}/100",
            metadata=result,
            confidence=0.8
        )
        
        return result
    
    def evaluate_multiple_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate multiple sources and rank by credibility."""
        self.log_thought(
            ThoughtType.INFO,
            f"Evaluating {len(sources)} sources",
            metadata={"num_sources": len(sources)}
        )
        
        evaluated_sources = []
        for source in sources:
            evaluation = self.evaluate_source(source)
            source['credibility_evaluation'] = evaluation
            evaluated_sources.append(source)
        
        # Sort by overall credibility
        evaluated_sources.sort(
            key=lambda x: x['credibility_evaluation']['overall_credibility'], 
            reverse=True
        )
        
        # Log summary
        avg_credibility = sum(s['credibility_evaluation']['overall_credibility'] for s in evaluated_sources) / len(evaluated_sources)
        self.log_thought(
            ThoughtType.INFO,
            f"Average source credibility: {avg_credibility:.1f}/100",
            metadata={
                "best_source": evaluated_sources[0]['url'] if evaluated_sources else None,
                "worst_source": evaluated_sources[-1]['url'] if evaluated_sources else None
            }
        )
        
        return evaluated_sources
    
    def recommend_sources(self, evaluated_sources: List[Dict[str, Any]], threshold: float = 70.0) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize sources by credibility and provide recommendations."""
        highly_credible = []
        moderately_credible = []
        low_credibility = []
        
        for source in evaluated_sources:
            credibility = source['credibility_evaluation']['overall_credibility']
            
            if credibility >= threshold:
                highly_credible.append(source)
            elif credibility >= 50:
                moderately_credible.append(source)
            else:
                low_credibility.append(source)
        
        self.log_thought(
            ThoughtType.DECIDING,
            f"Source recommendations: {len(highly_credible)} highly credible, "
            f"{len(moderately_credible)} moderate, {len(low_credibility)} low",
            metadata={
                "threshold": threshold,
                "highly_credible_count": len(highly_credible),
                "moderate_count": len(moderately_credible),
                "low_count": len(low_credibility)
            }
        )
        
        return {
            "highly_credible": highly_credible,
            "moderately_credible": moderately_credible,
            "low_credibility": low_credibility,
            "recommendation": "Use highly credible sources as primary references"
        }
    
    def _score_domain(self, domain: str) -> float:
        """Score a domain based on known authority."""
        domain_lower = domain.lower()
        
        # Check for authoritative domains
        for auth_domain in self.AUTHORITATIVE_DOMAINS:
            if auth_domain in domain_lower or domain_lower.endswith(f".{auth_domain}"):
                return 85.0
        
        # Check TLDs
        if domain_lower.endswith('.gov'):
            return 90.0
        elif domain_lower.endswith('.edu') or domain_lower.endswith('.ac.uk'):
            return 85.0
        elif domain_lower.endswith('.org'):
            return 70.0
        
        # Check caution domains
        for caution_domain in self.CAUTION_DOMAINS:
            if caution_domain in domain_lower:
                return 30.0
        
        # Default middle score for unknown domains
        return 50.0
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except:
            return ""
    
    def _extract_score(self, text: str, marker: str) -> float:
        """Extract a numerical score from response text."""
        try:
            lines = text.split('\n')
            for line in lines:
                if marker in line:
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
                    parts = line.split(':', 1)
                    if len(parts) > 1 and parts[1].strip():
                        result.append(parts[1].strip())
                elif capture and line.strip() and any(m in line for m in ['SCORE:', 'TYPE:', 'INDICATORS:', 'WARNINGS:', 'EVALUATION:']):
                    break
                elif capture and line.strip():
                    result.append(line.strip())
            
            return '\n'.join(result)
        except:
            return ""