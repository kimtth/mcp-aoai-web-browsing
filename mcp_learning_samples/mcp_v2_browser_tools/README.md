# MCP v2 — Browser tools

Compare the same Playwright operations with the
[core MCP 2026-07-28 specification](https://modelcontextprotocol.io/specification/2026-07-28).
[server.py](server.py) declares `playwright_navigate` (title, final URL and up to
2,000 characters of body text) and `playwright_screenshot` (800 × 600 viewport PNG).
[client.py](client.py) explicitly selects `Client(..., mode="2026-07-28")`
instead of calling the earlier `initialize()` API, and traces outgoing POST
messages and MCP headers. The v2 comparison label follows the
[specification references](../../README.md#specification-references),
not an official core major version, SDK version or MCP Apps extension version.

**Blocked and unverified:** the approved package proxy could not resolve
`mcp==2.2.0`. The SDK 2 API wiring and end-to-end browser flow have not been
verified. The commands below are a future manual check, not a record of a
passing run. Do not substitute SDK 1 or infer success from the OAuth stdlib lab.

## Setup when the pinned SDK is available

Use Python 3.13+ and `uv`, from the repository root. No LLM API key is needed.
[pyproject.toml](pyproject.toml) requires MCP SDK 2.2.0, Playwright 1.58.0 and
`httpx2>=2.5,<3`. Install only into this sample's isolated environment:

```powershell
uv sync --directory mcp_learning_samples/mcp_v2_browser_tools --default-index https://packagefeedproxy.microsoft.io/pypi/simple/
uv run --directory mcp_learning_samples/mcp_v2_browser_tools --no-sync playwright install chromium
```

If sync cannot resolve the pinned SDK, stop here. Do not bypass the approved
proxy or disable TLS verification. Chromium is a separate download subject to
organizational policy.

## Manual check in two terminals

After setup succeeds, open both terminals at the repository root. Port **8012**
must be free.

**Terminal 1 — server (leave running):**

```powershell
uv run --directory mcp_learning_samples/mcp_v2_browser_tools --no-sync python server.py
```

**Terminal 2 — client:**

```powershell
uv run --directory mcp_learning_samples/mcp_v2_browser_tools --no-sync python client.py https://example.com
```

The intended endpoint is `http://127.0.0.1:8012/mcp`; inspect the printed protocol,
tool list and page result. Omitting the URL uses `https://example.com`.
For an additional screenshot tool call:

```powershell
uv run --directory mcp_learning_samples/mcp_v2_browser_tools --no-sync python client.py https://example.com --screenshot
```

The CLI is written to print screenshot content types and MIME types, not display
or save the PNG. Stop the server with Ctrl+C when finished.

Each tool is written to open and close a fresh browser, so calls do not share
page state. HTTP(S) input validation is not a destination allowlist; there is
no authentication. Use only trusted URLs in this local teaching sample, not as
a production browser service.

[All learning samples](../../README.md#learning-samples)