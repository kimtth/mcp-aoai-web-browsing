from typing import Literal

from fastmcp import FastMCP
from pydantic import BaseModel


class LLMConfig(BaseModel):
    """Configuration for LLM client"""
    api_key: str
    model: str | None = None
    base_url: str | None = None
    temperature: float | None = 0.7
    max_tokens: int = 2000
    # Select the request field explicitly; deployment names do not imply capabilities.
    token_limit_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    # Azure OpenAI specific parameters
    api_version: str | None = None
    azure_endpoint: str | None = None
    deploy_name: str | None = None


class MCPServerConfig(BaseModel):
    """Configuration for connecting to an external MCP server via stdio"""
    command: str
    args: list[str] = []
    env: dict[str, str] | None = None


class BridgeConfig(BaseModel):
    """Configuration for the MCP-LLM Bridge"""
    mcp: FastMCP | None = None  # In-process FastMCP server
    server_config: MCPServerConfig | None = None  # External MCP server (stdio)
    llm_config: LLMConfig
    system_prompt: str | None = None

    class Config:
        arbitrary_types_allowed = True

