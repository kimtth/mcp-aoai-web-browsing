"""Real SDK v2 OAuth flow, with only login/consent and callback delivery simulated."""

from support.runtime_check import require_sdk_v2

require_sdk_v2()

import asyncio
import json
from urllib.parse import urlsplit

import httpx2
from mcp import Client
from mcp.client.auth import AuthorizationCodeResult, OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from support.auth_rules import ISSUER, REDIRECT, RESOURCE, SCOPE, callback_values


class MemoryStorage:
    def __init__(self) -> None:
        self.tokens: OAuthToken | None = None
        self.info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.info = client_info


async def main() -> None:
    received: dict[str, str] = {}

    async def simulate_user_agent(authorization_url: str) -> None:
        # Only this loopback fixture may auto-approve; never send a real login here.
        parts = urlsplit(authorization_url)
        if parts._replace(query="").geturl() != ISSUER + "/authorize":
            raise ValueError("Refusing automatic login to an unexpected authorization endpoint")
        async with httpx2.AsyncClient(timeout=10, trust_env=False, follow_redirects=False) as http:
            response = await http.get(authorization_url)
        if response.status_code != 302:
            raise ValueError("The local authorization fixture did not return a callback")
        received.clear()
        received.update(callback_values(response.headers["location"]))
        print("SIMULATED LOGIN: received a callback; code and state are not logged")

    async def callback() -> AuthorizationCodeResult:
        # SDK v1 returned (code, state); v2 must also receive the unmodified issuer.
        # OAuthClientProvider performs the state/issuer check BEFORE token exchange.
        return AuthorizationCodeResult(
            code=received.get("code", ""), state=received.get("state"), iss=received.get("iss"),
        )

    oauth = OAuthClientProvider(
        server_url=RESOURCE,
        client_metadata=OAuthClientMetadata(
            client_name="Local browser auth demo", redirect_uris=[REDIRECT],
            application_type="native", token_endpoint_auth_method="none",
            grant_types=["authorization_code"], response_types=["code"], scope=SCOPE,
        ),
        storage=MemoryStorage(), redirect_handler=simulate_user_agent, callback_handler=callback,
    )
    async with httpx2.AsyncClient(timeout=30, trust_env=False) as probe:
        denied = await probe.post(RESOURCE, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        if denied.status_code != 401:
            raise RuntimeError(f"Expected HTTP 401 without a token, got {denied.status_code}")
        print("WITHOUT TOKEN:", denied.status_code)
        print("DISCOVERY CHALLENGE:", denied.headers.get("www-authenticate"))
    async with httpx2.AsyncClient(auth=oauth, timeout=30, trust_env=False) as http:
        transport = streamable_http_client(RESOURCE, http_client=http)
        async with Client(transport, mode="2026-07-28") as client:
            tools = await client.list_tools()
            print("AUTHENTICATED TOOLS:", [tool.name for tool in tools.tools])
            result = await client.call_tool("read_demo_page", {})
            if result.is_error:
                raise RuntimeError("Authenticated browser tool failed")
            print("PAGE:", json.dumps(result.structured_content, indent=2))


if __name__ == "__main__":
    asyncio.run(main())