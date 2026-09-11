"""Protected SDK v2 HTTP browser tool; requires the separate local auth fixture."""

from support.runtime_check import require_sdk_v2

require_sdk_v2()

import time

import httpx2
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from playwright.async_api import async_playwright
from support.auth_rules import ISSUER, RESOURCE, SCOPE


class LocalTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        """Introspect opaque tokens; never accept a merely decoded token as proof."""
        try:
            async with httpx2.AsyncClient(timeout=5, trust_env=False) as http:
                response = await http.post(ISSUER + "/introspect", data={"token": token})
                response.raise_for_status()
                data = response.json()
            if not isinstance(data, dict):
                return None
            if (data.get("active") is not True or data.get("iss") != ISSUER
                    or data.get("aud") != RESOURCE or data.get("exp", 0) <= time.time()):
                return None
            if not isinstance(data.get("scope"), str) or not isinstance(data.get("client_id"), str):
                return None
            return AccessToken(
                token=token, client_id=data["client_id"], scopes=data["scope"].split(),
                expires_at=data["exp"], resource=data["aud"],
            )
        except (httpx2.HTTPError, ValueError, KeyError, TypeError):
            return None  # Fail closed when the trusted local issuer is unavailable/malformed.


mcp = MCPServer(
    "browser-v2-auth", version="0.1.0", token_verifier=LocalTokenVerifier(),
    auth=AuthSettings(issuer_url=ISSUER, resource_server_url=RESOURCE, required_scopes=[SCOPE]),
)


@mcp.tool()
async def read_demo_page() -> dict[str, str]:
    """Read a local HTML page in Chromium, only after bearer authentication."""
    token = get_access_token()
    if token is None:
        raise ValueError("An authenticated HTTP request is required")
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            page = await browser.new_page()
            await page.set_content(
                "<!doctype html><html lang='en'><title>Authenticated browser demo</title>"
                "<body><h1>Protected page read</h1><p>This local fixture is read by "
                "Playwright after MCP authentication succeeds.</p></body></html>"
            )
            return {
                "title": await page.title(), "text": await page.locator("body").inner_text(),
                "client_id": token.client_id, "source": "local HTML fixture; no network fetch",
            }
        finally:
            await browser.close()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8021, json_response=True)