"""Configuration management for the research system."""
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ModelConfig(BaseModel):
    """Configuration for a single model."""
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: int = 2048
    description: str = ""

class AgentConfig(BaseModel):
    """Configuration for agent settings."""
    min_sub_researchers: int = 3
    max_sub_researchers: int = 5
    default_sub_researchers: int = 4

class Settings(BaseSettings):
    """Application settings from environment variables."""
    # API Keys
    tavily_api_key: str = Field(default="", env="TAVILY_API_KEY")
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_access_key_id: str = Field(default="", env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", env="AWS_SECRET_ACCESS_KEY")
    
    # Model IDs (can be overridden by environment)
    lead_researcher_model: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        env="LEAD_RESEARCHER_MODEL"
    )
    sub_researcher_model: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        env="SUB_RESEARCHER_MODEL"
    )
    citation_model: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        env="CITATION_MODEL"
    )
    
    # Search Configuration
    tavily_search_depth: str = Field(default="basic", env="TAVILY_SEARCH_DEPTH")
    max_search_results: int = Field(default=5, env="MAX_SEARCH_RESULTS")
    
    # Cost Tracking
    monthly_budget_usd: float = Field(default=50.0, env="MONTHLY_BUDGET_USD")
    alert_at_percent: float = Field(default=80.0, env="ALERT_AT_PERCENT")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

class ConfigManager:
    """Manages configuration from YAML files and environment."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config")
        self.settings = Settings()
        self._models_config = self._load_models_config()
        self._pricing = self._load_pricing()
        
    def _load_models_config(self) -> Dict[str, Any]:
        """Load models configuration from YAML."""
        config_path = self.config_dir / "models.yaml"
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        return {}
    
    def _load_pricing(self) -> Dict[str, Dict[str, float]]:
        """Load model pricing information."""
        return self._models_config.get("pricing", {})
    
    def get_model_config(self, agent_type: str) -> ModelConfig:
        """Get model configuration for a specific agent type."""
        models = self._models_config.get("models", {})
        
        # Override with environment variables if set
        if agent_type == "lead_researcher" and self.settings.lead_researcher_model:
            models.setdefault("lead_researcher", {})["model_id"] = self.settings.lead_researcher_model
        elif agent_type == "sub_researcher" and self.settings.sub_researcher_model:
            models.setdefault("sub_researcher", {})["model_id"] = self.settings.sub_researcher_model
        elif agent_type == "citation_agent" and self.settings.citation_model:
            models.setdefault("citation_agent", {})["model_id"] = self.settings.citation_model
            
        config_data = models.get(agent_type, {})
        return ModelConfig(**config_data)
    
    def get_agent_config(self) -> AgentConfig:
        """Get agent configuration settings."""
        agents = self._models_config.get("agents", {})
        return AgentConfig(**agents)
    
    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a specific model usage."""
        pricing = self._pricing.get(model_id, {})
        input_cost = pricing.get("input", 0) * (input_tokens / 1_000_000)
        output_cost = pricing.get("output", 0) * (output_tokens / 1_000_000)
        return input_cost + output_cost
    
    def get_available_models(self) -> Dict[str, str]:
        """Get list of available models with descriptions."""
        models = self._models_config.get("models", {})
        return {
            name: config.get("description", config.get("model_id", ""))
            for name, config in models.items()
        }

# Global config instance
config = ConfigManager()