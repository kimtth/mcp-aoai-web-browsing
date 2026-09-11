"""Print actual HTTP requests so the initialization sequence is visible."""

import argparse
import asyncio
import json

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def trace(request: httpx.Request) -> None:
    if request.method == "POST":
        print("SEND", json.loads(request.content))
        print("SESSION", request.headers.get("mcp-session-id", "(none)"))


async def main(url: str, screenshot: bool = False) -> None:
    async with (
        httpx.AsyncClient(event_hooks={"request": [trace]},
                         timeout=30, trust_env=False) as http,
        streamable_http_client("http://127.0.0.1:8011/mcp", http_client=http) as streams,
    ):
        read, write, get_session_id = streams
        async with ClientSession(read, write) as client:
            initialized = await client.initialize()  # Required in this protocol era.
            print("PROTOCOL", initialized.protocolVersion)
            print("SESSION CREATED", bool(get_session_id()))
            tools = await client.list_tools()
            print("TOOLS", [tool.name for tool in tools.tools])
            result = await client.call_tool("playwright_navigate", {"url": url})
            if result.isError:
                raise RuntimeError(result.content)
            print("PAGE", result.structuredContent)
            if screenshot:
                image = await client.call_tool("playwright_screenshot", {"url": url})
                if image.isError:
                    raise RuntimeError(image.content)
                print("SCREENSHOT", [(item.type, getattr(item, "mimeType", None))
                                     for item in image.content])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="https://example.com")
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.screenshot))