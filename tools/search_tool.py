"""Tavily search tool with caching and result management."""
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import sqlite3
from tavily import TavilyClient
from src.config import config

class SearchCache:
    """SQLite-based cache for search results."""
    
    def __init__(self, cache_dir: Path = Path("data/cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "search_cache.db"
        self._init_db()
        
    def _init_db(self):
        """Initialize the cache database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT,
                    results TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            ''')
            conn.commit()
    
    def get(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached results for a query."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT results FROM search_cache WHERE query_hash = ? AND expires_at > ?',
                (query_hash, datetime.now())
            )
            row = cursor.fetchone()
            
        if row:
            return json.loads(row[0])
        return None
    
    def set(self, query: str, results: List[Dict[str, Any]], ttl_hours: int = 24):
        """Cache search results."""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT OR REPLACE INTO search_cache 
                   (query_hash, query, results, created_at, expires_at) 
                   VALUES (?, ?, ?, ?, ?)''',
                (query_hash, query, json.dumps(results), datetime.now(), expires_at)
            )
            conn.commit()
    
    def clear_expired(self):
        """Clear expired cache entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM search_cache WHERE expires_at < ?', (datetime.now(),))
            conn.commit()

class TavilySearchTool:
    """Enhanced Tavily search tool with caching and usage tracking."""
    
    def __init__(self, debug: bool = False):
        self.api_key = config.settings.tavily_api_key
        self.debug = debug
        
        if self.debug:
            print(f"[DEBUG] Initializing Tavily with API key: {'*' * 10 if self.api_key else 'None'}")
        
        if not self.api_key:
            raise ValueError("Tavily API key not found in configuration")
            
        self.client = TavilyClient(api_key=self.api_key)
        self.cache = SearchCache()
        self.search_count = 0
        self.cache_hits = 0
        
    def search(
        self,
        query: str,
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Perform a search using Tavily API with caching.
        
        Args:
            query: Search query
            search_depth: 'basic' or 'advanced' (default from config)
            max_results: Maximum number of results (default from config)
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            use_cache: Whether to use cached results
            
        Returns:
            Dict containing search results and metadata
        """
        # Check cache first
        if use_cache:
            cached_results = self.cache.get(query)
            if cached_results:
                self.cache_hits += 1
                if self.debug:
                    print(f"[DEBUG] Cache hit for query: {query}")
                return {
                    'results': cached_results,
                    'from_cache': True,
                    'search_count': self.search_count,
                    'cache_hits': self.cache_hits
                }
        
        # Perform search
        search_depth = search_depth or config.settings.tavily_search_depth
        max_results = max_results or config.settings.max_search_results
        
        if self.debug:
            print(f"[DEBUG] Performing search:")
            print(f"  Query: {query}")
            print(f"  Depth: {search_depth}")
            print(f"  Max Results: {max_results}")
            print(f"  Include Domains: {include_domains}")
            print(f"  Exclude Domains: {exclude_domains}")
        
        try:
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            
            self.search_count += 1
            
            if self.debug:
                print(f"[DEBUG] Search successful. Response contains {len(response.get('results', []))} results")
            
            # Process results
            results = []
            for result in response.get('results', []):
                processed_result = {
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', ''),
                    'score': result.get('score', 0.0),
                    'published_date': result.get('publishedDate', ''),
                    'domain': self._extract_domain(result.get('url', ''))
                }
                results.append(processed_result)
            
            # Cache results
            if use_cache:
                self.cache.set(query, results)
            
            # Clear expired cache entries periodically
            if self.search_count % 10 == 0:
                self.cache.clear_expired()
            
            return {
                'results': results,
                'from_cache': False,
                'search_count': self.search_count,
                'cache_hits': self.cache_hits,
                'query': query,
                'search_depth': search_depth
            }
            
        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Search failed with error: {str(e)}")
                import traceback
                print(f"[DEBUG] Full traceback:")
                traceback.print_exc()
                
            return {
                'results': [],
                'error': str(e),
                'search_count': self.search_count,
                'cache_hits': self.cache_hits,
                'query': query
            }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return ""
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get search usage statistics."""
        return {
            'total_searches': self.search_count,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': self.cache_hits / max(1, self.search_count + self.cache_hits),
            'remaining_searches': 1000 - self.search_count  # Assuming free tier
        }
    
    def format_results_for_llm(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for LLM consumption."""
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. **{result['title']}**\n"
                f"   URL: {result['url']}\n"
                f"   Content: {result['content'][:500]}...\n"
                f"   Relevance: {result['score']:.2f}\n"
            )
        return "\n".join(formatted)