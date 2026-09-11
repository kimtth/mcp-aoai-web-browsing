"""Real stdio calls and real Chromium against the network-free demo page."""

import base64
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport

from server import allow_example_only


class BrowserAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_app_and_browser_over_stdio(self):
        transport = PythonStdioTransport(
            Path(__file__).with_name("server.py"), keep_alive=False,
        )
        async with Client(transport) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            uri = tools["browser_panel"].meta["ui"]["resourceUri"]
            self.assertEqual(uri, "ui://prefab/renderer.html")
            self.assertEqual(
                tools["inspect_page"].meta["ui"]["visibility"], ["app", "model"],
            )
            resources = await client.read_resource(uri)
            self.assertIn("text/html", resources[0].mimeType)
            shell = (await client.call_tool("browser_panel")).structured_content
            wire = json.dumps(shell)
            self.assertIn('"toolCall"', wire)
            self.assertIn('"Slot"', wire)
            self.assertIn('"onError"', wire)
            self.assertFalse(shell["state"]["busy"])
            result = await client.call_tool("inspect_page", {"page_id": "demo"})
            state = result.structured_content["state"]
            self.assertEqual(state["title"], "MCP Apps reading demo")
            self.assertIn("Playwright reads this local fixture", state["text"])
            self.assertIn("no network", state["source"])
            png = base64.b64decode(state["screenshot"].split(",", 1)[1])
            self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(int.from_bytes(png[16:20], "big"), 800)
            rejected = await client.call_tool(
                "inspect_page", {"page_id": "https://localhost/"}, raise_on_error=False,
            )
            self.assertTrue(rejected.is_error)

    async def test_network_allowlist(self):
        for url, allowed in [
            ("https://example.com/", True),
            ("https://example.com/site.css", True),
            ("http://example.com/", False),
            ("https://example.com.evil.test/", False),
            ("https://example.com@localhost/", False),
            ("https://127.0.0.1/", False),
            ("file:///etc/passwd", False),
        ]:
            with self.subTest(url=url):
                route = AsyncMock()
                route.request.url = url
                await allow_example_only(route)
                if allowed:
                    route.continue_.assert_awaited_once()
                    route.abort.assert_not_awaited()
                else:
                    route.abort.assert_awaited_once()
                    route.continue_.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()