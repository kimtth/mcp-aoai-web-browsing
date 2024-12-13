from typing import Dict, List, Any, Optional
from openai import AzureOpenAI, OpenAI
from .config import LLMConfig
from loguru import logger


class LLMResponse:
    """Standardized response format focusing on tool handling"""
    def __init__(self, completion: Any):
        self.completion = completion
        self.choice = completion.choices[0]
        self.message = self.choice.message
        self.stop_reason = self.choice.finish_reason
        self.is_tool_call = self.stop_reason == "tool_calls"
        
        # Format content for bridge compatibility
        self.content = self.message.content if self.message.content is not None else ""
        self.tool_calls = self.message.tool_calls if hasattr(self.message, "tool_calls") else None
        
        # Debug logging
        logger.debug(f"Raw completion: {completion}")
        logger.debug(f"Message content: {self.content}")
        logger.debug(f"Tool calls: {self.tool_calls}")
        
    def get_message(self) -> Dict[str, Any]:
        """Get standardized message format"""
        return {
            "role": "assistant",
            "content": self.content,
            "tool_calls": self.tool_calls
        }

class LLMClient:
    """Client for interacting with OpenAI-compatible LLMs"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        if hasattr(config, 'azure_endpoint') and config.azure_endpoint:
            self.client = AzureOpenAI(
                api_version=config.api_version,
                azure_endpoint=config.azure_endpoint,
                api_key=config.api_key,
            )
        else:
            self.client = OpenAI(
                api_key=config.api_key,
                base_url=config.base_url
            )
        self.tools = []
        self.messages = []
        self.system_prompt = None
    
    def _prepare_messages(self) -> List[Dict[str, Any]]:
        """Prepare messages for API call"""
        formatted_messages = []
        
        if self.system_prompt:
            formatted_messages.append({
                "role": "system",
                "content": self.system_prompt
            })
            
        formatted_messages.extend(self.messages)
        return formatted_messages
    
    async def invoke_with_prompt(self, prompt: str) -> LLMResponse:
        """Send a single prompt to the LLM"""
        self.messages.append({
            "role": "user",
            "content": prompt
        })
        
        return await self.invoke([])
    
    async def invoke(self, tool_results: Optional[List[Dict[str, Any]]] = None) -> LLMResponse:
        """Invoke the LLM with optional tool results"""
        if tool_results:
            for result in tool_results:
                self.messages.append({
                    "role": "tool",
                    "content": str(result.get("output", "")),  # Convert to string and provide default
                    "tool_call_id": result["tool_call_id"]
                })
        
        completion = self.client.chat.completions.create(
            # To handle Azure OpenAI specific parameters
            model= self.config.deploy_name if hasattr(self.config, 'azure_endpoint') else self.config.model,
            messages=self._prepare_messages(),
            tools=self.tools if self.tools else None,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        response = LLMResponse(completion)
        self.messages.append(response.get_message())
        
        return response