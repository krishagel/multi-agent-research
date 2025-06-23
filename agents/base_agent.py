"""Base agent class with Bedrock integration."""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from crewai import Agent
from pydantic import Field, ConfigDict
from src.bedrock_client import bedrock
from src.config import config, ModelConfig
from src.thought_logger import thought_logger, ThoughtType
import uuid

class BedrockAgent(Agent, ABC):
    """Base agent class that integrates with AWS Bedrock."""
    
    # Define custom fields as Pydantic fields
    agent_type: str = Field(default="base")
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    bedrock_model_config: Optional[ModelConfig] = Field(default=None)
    request_count: int = Field(default=0)
    total_cost: float = Field(default=0.0)
    llm_function: Optional[Any] = Field(default=None)
    enable_thought_logging: bool = Field(default=True)
    
    # Configure Pydantic to allow extra attributes
    model_config = ConfigDict(extra='allow')
    
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        agent_type: str,
        bedrock_model_config: Optional[ModelConfig] = None,
        verbose: bool = True,
        allow_delegation: bool = False,
        tools: List[Any] = None
    ):
        # Get the model config first
        model_cfg = bedrock_model_config or config.get_model_config(agent_type)
        
        # Create a placeholder LLM function to pass to parent
        def placeholder_llm(prompt: str) -> str:
            return "Placeholder response"
        
        # Initialize CrewAI Agent with all required fields
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=verbose,
            allow_delegation=allow_delegation,
            tools=tools or [],
            llm=placeholder_llm,
            # Pass our custom fields through model initialization
            agent_type=agent_type,
            bedrock_model_config=model_cfg,
            request_count=0,
            total_cost=0.0
        )
        
        # Now create the actual LLM function with proper config
        self.llm_function = self._create_llm_function()
        
        # Log agent initialization
        if self.enable_thought_logging:
            self.log_thought(
                ThoughtType.INFO,
                f"Initialized {agent_type} agent: {role}",
                metadata={"goal": goal, "model": model_cfg.model_id}
            )
        
    def _create_llm_function(self):
        """Create a function that CrewAI can use as an LLM."""
        def llm_function(prompt: str) -> str:
            """Function to interact with Bedrock."""
            messages = [{"role": "user", "content": prompt}]
            
            response = bedrock.invoke_model(
                model_id=self.bedrock_model_config.model_id,
                messages=messages,
                temperature=self.bedrock_model_config.temperature,
                max_tokens=self.bedrock_model_config.max_tokens
            )
            
            # Update agent stats
            self.request_count += 1
            self.total_cost += response['_metadata']['cost']
            
            return bedrock.get_response_text(response)
        
        return llm_function
    
    @abstractmethod
    def prepare_prompt(self, task: Any) -> str:
        """Prepare the prompt for the specific agent type."""
        pass
    
    def invoke_llm(self, prompt: str, log_prompt: bool = True) -> str:
        """Invoke the LLM with a prompt."""
        if self.enable_thought_logging and log_prompt:
            self.log_thought(
                ThoughtType.ANALYZING,
                "Sending prompt to LLM",
                metadata={"prompt_preview": prompt[:200] + "..." if len(prompt) > 200 else prompt}
            )
        
        response = self.llm_function(prompt)
        
        if self.enable_thought_logging and log_prompt:
            self.log_thought(
                ThoughtType.ANALYZING,
                "Received LLM response",
                metadata={"response_preview": response[:200] + "..." if len(response) > 200 else response}
            )
        
        return response
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get agent-specific usage statistics."""
        return {
            'agent_type': getattr(self, 'agent_type', 'unknown'),
            'model_id': getattr(self.bedrock_model_config, 'model_id', 'unknown') if hasattr(self, 'bedrock_model_config') else 'unknown',
            'requests': getattr(self, 'request_count', 0),
            'total_cost': getattr(self, 'total_cost', 0.0),
            'average_cost_per_request': getattr(self, 'total_cost', 0.0) / max(1, getattr(self, 'request_count', 0))
        }
    
    def log_thought(
        self,
        thought_type: ThoughtType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None
    ):
        """Log a thought to the centralized thought logger."""
        if self.enable_thought_logging:
            thought_logger.log_thought(
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                thought_type=thought_type,
                content=content,
                metadata=metadata,
                confidence=confidence
            )