import base64
import json
from fastmcp import Context, FastMCP
from mcp.types import TextContent, ImageContent
from playwright.async_api import Page
from client_bridge.llm_client import LLMClient, LLMResponse
from client_bridge.llm_config import get_default_llm_config
from server.browser_manager import BrowserManager


class BrowserNavigationServer(FastMCP):
    def __init__(self, server_name="browser-navigator-server"):
        super().__init__(server_name)
        self.mcp = self
        self.browser_manager = BrowserManager()
        self.llm_config = get_default_llm_config()
        self.llm_client = LLMClient(self.llm_config)
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

                if selector:
                    element = await page.query_selector(selector)
                    if not element:
                        return f"Element not found: {selector}"
                    screenshot = await element.screenshot(type="png")
                else:
                    screenshot = await page.screenshot(type="png", full_page=True)

                # Convert the screenshot to a base64 string
                screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")
                self.screenshots[name] = screenshot_base64
                return [
                    TextContent(type="text", text=f"Screenshot {name} taken"),
                    ImageContent(
                        type="image", data=screenshot_base64, mimeType="image/png"
                    ),
                ]
            except Exception as e:
                raise ValueError(f"Screenshot failed: {e}")

        @self.mcp.tool()
        async def playwright_click(selector: str):
            """Click an element on the page."""
            try:
                page: Page = await self.browser_manager.ensure_browser()
                await page.wait_for_selector(selector)
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

        @self.mcp.tool()
        async def extract_selector_by_page_content(user_message: str) -> str:
            """Try to find a css selector by current page content."""
            # Ensure the browser page is available
            page = await self.browser_manager.ensure_browser()

            # Get the HTML content of the page
            html_content = await page.content()

            # Prepare the prompt for the LLM
            prompt = (
                "Given the following HTML content of a web page:\n\n"
                f"{html_content}\n\n"
                f"User request: '{user_message}'\n\n"
                "Provide the CSS selector that best matches the user's request. Return only the CSS selector."
            )

            # Use the LLM client to generate the selector
            llm_response: LLMResponse = await self.llm_client.invoke_with_prompt(prompt)
            selector: str = llm_response.content

            # Return the selector
            return selector.strip()

        # Long-running example to read all screenshots from a list of file names
        @self.mcp.tool()
        async def read_all_screenshots(file_name_list: list[str], ctx: Context) -> str:
            """Read all screenshots from a list of file names."""
            for i, file_name in enumerate(file_name_list):
                ctx.info(f"Processing {file_name}...")
                await ctx.report_progress(i, len(file_name_list))

                # Read another resource if needed
                await ctx.read_resource(f"screenshot://{file_name}")

            return "Processing complete"

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


app = BrowserNavigationServer()
