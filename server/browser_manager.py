from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self):
        self._playwright = None
        self.browser = None
        self.page = None
        self.console_logs = []

    async def ensure_browser(self):
        if not self.browser:
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(headless=False)
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

    async def close(self):
        """Close browser and playwright instance"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
