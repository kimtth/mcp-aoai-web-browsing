"""Capture real Prefab previews, not an MCP Apps host integration.

Run with the apps_browser sample's Python environment from the repository root.
"""

import asyncio
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "screenshots"


def load_sample(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "mcp_learning_samples" / name / "server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    reactive = load_sample("apps_reactive")
    browser_sample = load_sample("apps_browser")
    result = await browser_sample.inspect_page("demo")
    pages = {
        "/reactive": reactive.reading_card().html(),
        "/browser": browser_sample.browser_panel().html(),
        "/result": result.html(),
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            html = pages.get(self.path)
            self.send_response(200 if html else 404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write((html or "Not found").encode())

        def log_message(self, *_):
            pass

    OUTPUT.mkdir(exist_ok=True)
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={"width": 1100, "height": 850}, device_scale_factor=1)
                base = f"http://127.0.0.1:{server.server_port}"
                await page.goto(base + "/reactive")
                await page.get_by_role("button", name="Reset topic").wait_for()
                await page.get_by_role("textbox").fill("MCP Apps in action")
                await expect(page.get_by_role("heading", name="MCP Apps in action", exact=True)).to_be_visible()
                await page.screenshot(path=str(OUTPUT / "apps-reactive.png"), full_page=True)
                await page.get_by_role("button", name="Reset topic").click()
                await expect(page.get_by_role("heading", name="MCP Apps", exact=True)).to_be_visible()
                await page.goto(base + "/browser")
                await page.get_by_role("button", name="Read page").wait_for()
                await page.screenshot(path=str(OUTPUT / "apps-browser-shell.png"), full_page=True)
                await page.goto(base + "/result")
                await page.get_by_role("heading", name="MCP Apps reading demo", exact=True).wait_for()
                await page.locator("img").evaluate_all(
                    "imgs => Promise.all(imgs.map(img => img.decode()))"
                )
                await page.screenshot(path=str(OUTPUT / "apps-browser-result.png"), full_page=True)
                await browser.close()
        finally:
            server.shutdown()
            worker.join()
    print("Captured 3 real previews. Reactive input/reset verified; browser result uses local Playwright HTML.")
    print("No Apps host callbacks or SDK v2 integration are claimed.")


if __name__ == "__main__":
    asyncio.run(main())