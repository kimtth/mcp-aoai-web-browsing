"""MCP App shell -> CallTool -> fresh Playwright page -> Slot result."""

import base64
from typing import Literal
from urllib.parse import urlsplit

from fastmcp import FastMCP
from fastmcp.apps import AppConfig
from playwright.async_api import Route, async_playwright
from prefab_ui.actions import SetState
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Column,
    Heading,
    Image,
    Label,
    Select,
    SelectOption,
    Slot,
    Text,
)
from prefab_ui.rx import RESULT, Rx

mcp = FastMCP("prefab-browser")

# A deterministic browser fixture, not a fetched website or fabricated live result.
DEMO_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>MCP Apps reading demo</title><body>
<h1>A page inside an MCP App</h1>
<p>Playwright reads this local fixture in a fresh browser context.</p>
<p>The app calls a server tool and renders its response in a Slot.</p>
</body></html>"""


@mcp.tool(app=True)
def browser_panel() -> PrefabApp:
    """Open the browser panel to read a demo page or example.com with Playwright."""
    busy = Rx("busy")
    with Column(gap=4, css_class="max-w-2xl mx-auto p-6") as view:
        Badge("02 / Server callback", variant="secondary")
        Heading("Read a page")
        Text("Each click opens a fresh browser. No account or API key is needed.")
        Label("Page", for_id="page-choice")
        with Select(id="page-choice", name="page_id"):
            SelectOption(label="Local demo (no network)", value="demo")
            SelectOption(label="example.com (network required)", value="example")
        Button(
            busy.then("Reading...", "Read page"),
            disabled=busy,
            on_click=[
                SetState("busy", True),
                SetState("error", ""),
                CallTool(
                    "inspect_page",
                    arguments={"page_id": Rx("page_id")},
                    on_success=[SetState("result", RESULT), SetState("busy", False)],
                    on_error=[SetState("error", "{{ $error }}"), SetState("busy", False)],
                ),
            ],
        )
        Text("{{ error }}")
        with Slot("result"):
            Text("Choose a page, then click Read page. Nothing has been fetched yet.")
    return PrefabApp(
        view=view,
        state={"page_id": "demo", "busy": False, "error": "", "result": None},
    )


async def allow_example_only(route: Route) -> None:
    """Keep redirects and subresources on the single permitted HTTPS origin."""
    url = urlsplit(route.request.url)
    if (url.scheme, url.netloc) == ("https", "example.com"):
        await route.continue_()
    else:
        await route.abort()


@mcp.tool(app=AppConfig(visibility=["app", "model"]))
async def inspect_page(page_id: Literal["demo", "example"] = "demo") -> PrefabApp:
    """Read title/text and take a viewport PNG; callable by the app or model."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            context = await browser.new_context(
                viewport={"width": 800, "height": 450}, service_workers="block",
            )
            await context.route("**/*", allow_example_only)
            page = await context.new_page()
            if page_id == "demo":
                await page.set_content(DEMO_HTML)
                source = "Local HTML fixture (no network request)"
            else:
                response = await page.goto(
                    "https://example.com/", wait_until="domcontentloaded", timeout=15000,
                )
                if response is None or not response.ok:
                    raise ValueError("The page did not return a successful HTTP response")
                source = page.url
            result = {
                "title": await page.title(),
                "text": (await page.locator("body").inner_text())[:2000],
                "source": source,
                "screenshot": "data:image/png;base64," + base64.b64encode(
                    await page.screenshot()
                ).decode("ascii"),
            }
        finally:
            await browser.close()
    # Page text goes into state, not executable HTML or a template expression.
    with Column(gap=3) as view:
        Heading("{{ title }}", level=2)
        Text("{{ source }}")
        Text("{{ text }}", css_class="whitespace-pre-wrap")
        Image(src="{{ screenshot }}", alt="Page viewport captured by Playwright")
    return PrefabApp(view=view, state=result)


if __name__ == "__main__":
    mcp.run()