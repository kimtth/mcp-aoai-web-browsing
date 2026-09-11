"""Real stdio MCP checks; these do not substitute for an Apps host UI test."""

import json
import unittest
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport


class ReactiveAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_app_contract_over_stdio(self):
        transport = PythonStdioTransport(
            Path(__file__).with_name("server.py"), keep_alive=False,
        )
        async with Client(transport) as client:
            tools = await client.list_tools()
            self.assertEqual([tool.name for tool in tools], ["reading_card"])
            uri = tools[0].meta["ui"]["resourceUri"]
            self.assertEqual(uri, "ui://prefab/renderer.html")
            resources = await client.read_resource(uri)
            self.assertIn("text/html", resources[0].mimeType)
            self.assertIn("<html", resources[0].text.lower())
            result = await client.call_tool("reading_card")
            envelope = result.structured_content
            self.assertEqual(envelope["state"]["topic"], "MCP Apps")
            wire = json.dumps(envelope)
            self.assertIn('"setState"', wire)
            self.assertNotIn('"toolCall"', wire)
            self.assertIn("{{ topic", wire)
            self.assertIn("view", envelope)


if __name__ == "__main__":
    unittest.main()