# MCP v1 — Browser tools

Read a page with Playwright while observing MCP initialization, version
negotiation and HTTP session handling. [server.py](server.py) exposes
`playwright_navigate` (title, final URL and up to 2,000 characters of body text)
and `playwright_screenshot` (800 × 600 viewport PNG). [client.py](client.py)
prints outgoing POST messages, session information and tool results.

## Specification and dependencies

- [Core MCP 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
  and its [initialization lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
  describe the client/server protocol, not a Python SDK release number.
- The client calls `initialize()` and prints the negotiated `protocolVersion`;
  it does not hard-code the date. The installed `mcp==1.27.0` supports
  `2025-11-25` as its latest version, and negotiation to that date has been
  confirmed at runtime. This naming change does not represent a new test run.
- [pyproject.toml](pyproject.toml) pins MCP SDK 1.27.0, Playwright 1.58.0 and
  HTTPX 0.28.1; Python 3.13+ and `uv` are required. No LLM API key is needed.

## Setup

Run from the repository root; keep this sample's environment separate:

```powershell
uv sync --directory mcp_learning_samples/mcp_v1_browser_tools --default-index https://packagefeedproxy.microsoft.io/pypi/simple/
uv run --directory mcp_learning_samples/mcp_v1_browser_tools --no-sync playwright install chromium
```

Use the approved package proxy; do not bypass it or disable TLS verification.
Chromium is a separate download subject to organizational policy.

## Run in two terminals

Both terminals start at the repository root. Port **8011** must be free.

**Terminal 1 — server (leave running):**

```powershell
uv run --directory mcp_learning_samples/mcp_v1_browser_tools --no-sync python server.py
```

**Terminal 2 — client:**

```powershell
uv run --directory mcp_learning_samples/mcp_v1_browser_tools --no-sync python client.py https://example.com
```

The client connects to `http://127.0.0.1:8011/mcp`, initializes, lists tools and
reads the page. Omitting the URL uses `https://example.com`.
For an additional screenshot tool call:

```powershell
uv run --directory mcp_learning_samples/mcp_v1_browser_tools --no-sync python client.py https://example.com --screenshot
```

The screenshot response contains PNG data, but the CLI only prints content types
and MIME types; it does not display or save an image. Stop the server with Ctrl+C.

Each tool call opens and closes a fresh browser; navigation and screenshot calls
do not share page state. Only HTTP(S) input URLs are accepted, but there is no
destination allowlist or authentication. Use only trusted URLs in this local
teaching sample; it is not a production browser service or an MCP Apps UI.

[All learning samples](../../README.md#learning-samples)