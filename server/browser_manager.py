from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self):
        self.browser = None
        self.page = None
        self.console_logs = []
        self.screenshots = {}

    async def ensure_browser(self):
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=False)
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1,
            )
            self.page = await context.new_page()

            async def handle_console_message(msg):
                log_entry = f"[{msg.type}] {msg.text}"
                self.console_logs.append(log_entry)
                # Simulate a server notification
                print({
                    "method": "notifications/resources/updated",
                    "params": {"uri": "console://logs"},
                })

            self.page.on("console", handle_console_message)

        return self.page
