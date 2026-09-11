"""Minimal MCP App: reactive state stays in the renderer, not on the server."""

from fastmcp import FastMCP
from prefab_ui.actions import SetState
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    Column,
    Heading,
    Input,
    Label,
    Text,
)

mcp = FastMCP("prefab-reactive")


@mcp.tool(app=True)
def reading_card() -> PrefabApp:
    """Open an interactive reading card. Editing it makes no further tool calls."""
    with Column(gap=4, css_class="max-w-lg mx-auto p-6") as view:
        Badge("01 / Client-side state", variant="secondary")
        Heading("Your reading card")
        Text("Type a topic. The card updates instantly without another MCP request.")
        Label("Reading topic", for_id="topic")
        Input(id="topic", name="topic", placeholder="What are you reading about?")
        with Card(), CardContent():
            Heading("{{ topic }}", level=2)
            Text("This text follows the topic stored in this app's local state.")
        Button("Reset topic", on_click=SetState("topic", "MCP Apps"))
    return PrefabApp(view=view, state={"topic": "MCP Apps"})


if __name__ == "__main__":
    mcp.run()