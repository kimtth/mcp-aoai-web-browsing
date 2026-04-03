from typing import Any, List, Optional
from contextlib import AsyncExitStack
from loguru import logger
from fastmcp import FastMCP
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)


class MCPClient:
    """Client for interacting with MCP servers"""

    def __init__(self, mcp: FastMCP = None, *, server_config=None):
        self.mcp = mcp
        self.server_config = server_config
        self._session = None
        self._exit_stack: Optional[AsyncExitStack] = None

    async def connect(self):
        """Establishes connection to MCP server"""
        logger.debug("Connecting to MCP server...")
        try:
            self._exit_stack = AsyncExitStack()
            await self._exit_stack.__aenter__()

            if self.mcp:
                # In-memory connection (for in-process FastMCP server)
                self._session = await self._exit_stack.enter_async_context(
                    client_session(self.mcp._mcp_server)
                )
            elif self.server_config:
                # External server via stdio
                from mcp.client.stdio import stdio_client, StdioServerParameters
                from mcp import ClientSession

                params = StdioServerParameters(
                    command=self.server_config.command,
                    args=self.server_config.args,
                    env=self.server_config.env,
                )
                read_stream, write_stream = await self._exit_stack.enter_async_context(
                    stdio_client(params)
                )
                session = await self._exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await session.initialize()
                self._session = session
            else:
                raise ValueError("No MCP server or server_config provided")

            logger.debug("Connected to MCP server successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None
            logger.debug("Disconnected from MCP server")

    async def get_available_tools(self) -> List[Any]:
        """List available tools"""
        logger.debug("Requesting available tools from MCP server")
        try:
            if self._session:
                tools = await self._session.list_tools()
                logger.debug(f"Received tools from MCP server: {tools}")
                return tools
            # Fallback: per-operation session (backward compat for in-memory)
            async with client_session(self.mcp._mcp_server) as client:
                tools = await client.list_tools()
                logger.debug(f"Received tools from MCP server: {tools}")
                return tools
        except Exception as e:
            logger.error(f"Failed to get available tools: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Call a tool with given arguments"""
        try:
            if self._session:
                result = await self._session.call_tool(tool_name, arguments=arguments)
                logger.debug(f"Tool result: {result}")
                return result
            # Fallback: per-operation session (backward compat for in-memory)
            async with client_session(self.mcp._mcp_server) as client:
                result = await client.call_tool(tool_name, arguments=arguments)
                logger.debug(f"Tool result: {result}")
                return result
        except Exception as e:
            logger.error(f"Failed to call tool '{tool_name}': {e}")
            raise
