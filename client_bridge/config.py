from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Dict, List, Optional


class LLMConfig(BaseModel):
    """Configuration for LLM client"""
    api_key: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    # Azure OpenAI specific parameters
    api_version: Optional[str] = None
    azure_endpoint: Optional[str] = None
    deploy_name: Optional[str] = None


class MCPServerConfig(BaseModel):
    """Configuration for connecting to an external MCP server via stdio"""
    command: str
    args: List[str] = []
    env: Optional[Dict[str, str]] = None


class BridgeConfig(BaseModel):
    """Configuration for the MCP-LLM Bridge"""
    mcp: Optional[FastMCP] = None  # In-process FastMCP server
    server_config: Optional[MCPServerConfig] = None  # External MCP server (stdio)
    llm_config: LLMConfig
    system_prompt: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

