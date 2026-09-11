"""Pin modern mode: no initialize, discovery probe, or legacy fallback."""

import argparse
import asyncio
import json

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def trace(request: httpx2.Request) -> None:
    if request.method == "POST":
        print("SEND", json.loads(request.content))
        print("HEADERS", {key: value for key, value in request.headers.items()
                          if key.startswith("mcp-")})


async def main(url: str, screenshot: bool = False) -> None:
    async with httpx2.AsyncClient(event_hooks={"request": [trace]},
                                  timeout=30, trust_env=False) as http:
        transport = streamable_http_client("http://127.0.0.1:8012/mcp", http_client=http)
        async with Client(transport, mode="2026-07-28") as client:
            print("PROTOCOL", client.protocol_version)
            tools = await client.list_tools()
            print("TOOLS", [tool.name for tool in tools.tools])
            result = await client.call_tool("playwright_navigate", {"url": url})
            if result.is_error:
                raise RuntimeError(result.content)
            print("PAGE", result.structured_content)
            if screenshot:
                image = await client.call_tool("playwright_screenshot", {"url": url})
                if image.is_error:
                    raise RuntimeError(image.content)
                print("SCREENSHOT", [(item.type, getattr(item, "mime_type", None))
                                     for item in image.content])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="https://example.com")
    parser.add_argument("--screenshot", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.screenshot))