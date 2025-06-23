"""CrewAI-compatible wrapper for Tavily search tool."""
from typing import Type, Optional, Any
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from tools.search_tool import TavilySearchTool


class SearchInput(BaseModel):
    """Input schema for search tool."""
    query: str = Field(description="The search query to execute")
    max_results: Optional[int] = Field(default=5, description="Maximum number of results to return")


class CrewAISearchTool(BaseTool):
    """CrewAI-compatible search tool using Tavily."""
    
    name: str = "web_search"
    description: str = "Search the web for information using Tavily search engine"
    args_schema: Type[BaseModel] = SearchInput
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tavily_tool = TavilySearchTool()
    
    def _run(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any
    ) -> str:
        """Execute the search and return formatted results."""
        # Perform search
        search_results = self._tavily_tool.search(
            query=query,
            max_results=max_results,
            use_cache=True
        )
        
        # Format results for agent consumption
        if search_results.get('error'):
            return f"Search error: {search_results['error']}"
        
        results = search_results.get('results', [])
        if not results:
            return "No search results found."
        
        # Format results
        formatted = self._tavily_tool.format_results_for_llm(results[:max_results])
        return f"Search results for '{query}':\n\n{formatted}"
    
    @property
    def search_count(self) -> int:
        """Get the number of searches performed."""
        return self._tavily_tool.search_count
    
    @property
    def cache_hits(self) -> int:
        """Get the number of cache hits."""
        return self._tavily_tool.cache_hits