from typing import Any, List
from loguru import logger
from fastmcp import FastMCP
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)


class MCPClient:
    """Client for interacting with MCP servers"""

    def __init__(self, mcp: FastMCP):
        self.mcp = mcp

    async def connect(self):
        """Establishes connection to MCP server"""
        logger.debug("Connecting to MCP server...")
        try:
            async with client_session(self.mcp._mcp_server) as client:
                logger.debug("Connected to MCP server successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def get_available_tools(self) -> List[Any]:
        """List available tools"""
        logger.debug("Requesting available tools from MCP server")
        try:
            async with client_session(self.mcp._mcp_server) as client:
                tools = await client.list_tools()
                logger.debug(f"Received tools from MCP server: {tools}")
                return tools
        except Exception as e:
            RuntimeError("Failed to get available tools from MCP server")
            raise

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool with given arguments"""
        try:
            async with client_session(self.mcp._mcp_server) as client:
                result = await client.call_tool(tool_name, arguments=arguments)
                logger.debug(f"Tool result: {result}")
                return result
        except Exception as e:
            RuntimeError(f"Failed to call tool '{tool_name}' with arguments: {arguments}")
            raise
