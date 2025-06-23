"""AWS Bedrock client wrapper for LLM interactions."""
import json
import time
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
from src.config import config

class BedrockClient:
    """Wrapper for AWS Bedrock API with token counting and cost tracking."""
    
    def __init__(self):
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=config.settings.aws_region,
            aws_access_key_id=config.settings.aws_access_key_id,
            aws_secret_access_key=config.settings.aws_secret_access_key
        )
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0
        
    def invoke_model(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Invoke a Bedrock model with the given messages."""
        
        # Prepare the request body for Claude models
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
            
        try:
            start_time = time.time()
            
            response = self.client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Track usage
            usage = response_body.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            self.request_count += 1
            
            # Calculate cost
            cost = config.estimate_cost(model_id, input_tokens, output_tokens)
            self.total_cost += cost
            
            # Add metadata to response
            response_body['_metadata'] = {
                'model_id': model_id,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'cost': cost,
                'latency': time.time() - start_time,
                'total_cost': self.total_cost
            }
            
            return response_body
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ThrottlingException':
                # Implement exponential backoff
                time.sleep(2)
                return self.invoke_model(model_id, messages, temperature, max_tokens, system_prompt)
            else:
                raise Exception(f"Bedrock API error: {error_code} - {error_message}")
    
    def get_response_text(self, response: Dict[str, Any]) -> str:
        """Extract the text content from the model response."""
        content = response.get('content', [])
        if content and isinstance(content, list):
            return content[0].get('text', '')
        return ''
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            'total_requests': self.request_count,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'total_cost': self.total_cost,
            'average_cost_per_request': self.total_cost / max(1, self.request_count)
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.request_count = 0

# Global client instance
bedrock = BedrockClient()