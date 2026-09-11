"""SDK 2.x: the same browser tools, with the 2026-07-28 protocol."""

from urllib.parse import urlsplit

from mcp.server.mcpserver import Image, MCPServer
from playwright.async_api import async_playwright

mcp = MCPServer("browser-v2", version="0.1.0")


def check_url(url: str) -> None:
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("Only HTTP(S) pages are supported")


@mcp.tool()
async def playwright_navigate(url: str) -> dict[str, str]:
    """Open a URL in a fresh browser and return its title and visible text."""
    check_url(url)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return {"url": page.url, "title": await page.title(),
                    "text": (await page.locator("body").inner_text())[:2000]}
        finally:
            await browser.close()


@mcp.tool()
async def playwright_screenshot(url: str) -> Image:
    """Open a URL in a fresh browser and return a viewport PNG."""
    check_url(url)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            page = await browser.new_page(viewport={"width": 800, "height": 600})
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return Image(data=await page.screenshot(), format="png")
        finally:
            await browser.close()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8012,
            json_response=True)