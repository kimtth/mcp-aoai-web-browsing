import base64
import json
from fastmcp import FastMCP
from fastmcp.prompts.base import UserMessage
from mcp.types import TextContent, ImageContent
from playwright.async_api import Page
from server.browser_manager import BrowserManager


class BrowserNavigationServer(FastMCP):
    def __init__(self, server_name="browser-navigator-server"):
        super().__init__(server_name)
        self.mcp = self
        self.browser_manager = BrowserManager()
        self.screenshots = dict()
        self.register_tools()
        self.register_resources()
        self.register_prompts()

    def register_tools(self):
        @self.mcp.tool()
        async def playwright_navigate(url: str, timeout=30000, wait_until="load"):
            """Navigate to a URL."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                await page.goto(url, timeout=timeout, wait_until=wait_until)
                return f"Navigated to {url} with {wait_until} wait"
            except Exception as e:
                raise ValueError(f"Navigation failed: {e}")

        @self.mcp.tool()
        async def playwright_screenshot(
            name: str, selector: str = None, width: int = 800, height: int = 600
        ):
            """Take a screenshot of the current page or a specific element."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                element = await page.query_selector(selector) if selector else None
                screeenshot_options = {
                    "type": "png",
                    "full_page": True,
                    "element": element,
                    # "mask": True # TODO
                }

                if element:
                    screenshot = await page.screenshot(**screeenshot_options)
                    # Convert the screenshot to a base64 string
                    screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")
                    self.screenshots[name] = screenshot_base64
                    return [
                        TextContent(type="text", text=f"Screenshot {name} taken"),
                        ImageContent(
                            type="image", data=screenshot_base64, mimeType="image/png"
                        ),
                    ]
                else:
                    return f"Element not found: {selector}"
            except Exception as e:
                raise ValueError(f"Screenshot failed: {e}")

        @self.mcp.tool()
        async def playwright_click(selector: str):
            """Click an element on the page."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                await page.click(selector)
                return f"Clicked on {selector}"
            except Exception as e:
                raise ValueError(f"Failed to click: {e}")

        @self.mcp.tool()
        async def playwright_fill(selector: str, value: str):
            """Fill out an input field."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                await page.wait_for_selector(selector)
                await page.fill(selector, value)
                return f"Filled {selector} with {value}"
            except Exception as e:
                raise ValueError(f"Failed to fill: {e}")

        @self.mcp.tool()
        async def playwright_select(selector: str, value: str):
            """Select an element on the page with a Select tag."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                await page.wait_for_selector(selector)
                await page.select_option(selector, value)
                return f"Selected {value} in {selector}"
            except Exception as e:
                raise ValueError(f"Failed to select: {e}")

        @self.mcp.tool()
        async def playwright_hover(selector: str):
            """Hover over an element on the page."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                await page.wait_for_selector(selector)
                await page.hover(selector)
                return f"Hovered over {selector}"
            except Exception as e:
                raise ValueError(f"Failed to hover: {e}")

        @self.mcp.tool()
        async def playwright_evaluate(script: str):
            """Execute JavaScript in the browser console."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                script_result = await page.evaluate(
                    """
                (script) => {
                    const logs = [];
                    const originalConsole = { ...console };

                    ['log', 'info', 'warn', 'error'].forEach(method => {
                        console[method] = (...args) => {
                            logs.push(`[${method}] ${args.join(' ')}`);
                            originalConsole[method](...args);
                        };
                    });

                    try {
                        const result = eval(script);
                        Object.assign(console, originalConsole);
                        return { result, logs };
                    } catch (error) {
                        Object.assign(console, originalConsole);
                        throw error;
                    }
                }
                """,
                    script,
                )
                # Parentheses allow grouping multiple expressions in one line,
                # often used for long strings, tuples, or function arguments
                # that span multiple lines.
                return_string = (
                    "Execution result:\n"
                    + json.dumps(script_result["result"], indent=2)
                    + "\n\n"
                    + "Console output:\n"
                    + "\n".join(script_result["logs"])
                )
                return return_string
            except Exception as e:
                raise ValueError(f"Script execution failed: {e}")

    def register_resources(self):
        @self.mcp.resource("console://logs")
        async def get_console_logs() -> str:
            """Get a personalized greeting"""
            return TextContent(
                type="text", text="\n".join(self.browser_manager.console_logs)
            )

        @self.mcp.resource("screenshot://{name}")
        async def get_screenshot(name: str) -> str:
            """Get a screenshot by name"""
            screenshot_base64 = self.screenshots.get(name)
            if screenshot_base64:
                return ImageContent(
                    type="image",
                    data=screenshot_base64,
                    mimeType="image/png",
                    uri=f"screenshot://{name}",
                )
            else:
                raise ValueError(f"Screenshot {name} not found")

    def register_prompts(self):
        @self.mcp.prompt()
        async def hello_world(code: str) -> str:
            return f"Hello world:\n\n{code}"


""" 
When executing the MCP Inspector in a terminal, use the following command:

```bash
cmd> fastmcp dev ./server/browser_navigator_server.py:app
```

app = BrowserNavigationServer()

- `server/browser_navigator_server.py` specifies the file path.
- `app` refers to the server object created by `BrowserNavigationServer`.

After running the command, the following message will be displayed:

```
> Starting MCP Inspector...
> 🔍 MCP Inspector is up and running at http://localhost:5173 🚀
```

**Important:** Do not use `__main__` to launch the MCP Inspector. This will result in the following error:

    No server object found in **.py. Please either:
    1. Use a standard variable name (mcp, server, or app)
    2. Specify the object name with file:object syntax
"""
# app = BrowserNavigationServer()
print("BrowserNavigationServer is running...")
# print all attributes of the mcp
# print(dir(app))

# if __name__ == "__main__":
#     app = BrowserNavigationServer()
#     app.run()
#     print("BrowserNavigationServer is running...")
