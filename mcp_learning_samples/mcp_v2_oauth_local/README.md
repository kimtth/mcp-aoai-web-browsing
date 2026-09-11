# MCP v2 — Local OAuth introduction

Learn how an OAuth client obtains a resource-bound token before calling a
protected MCP browser tool, and why a wrong or missing callback issuer must
stop the flow before token exchange. No Azure OpenAI key or external page is needed.

**Status:** the stdlib fixture runs locally. Real SDK v2 integration remains
**unverified**: `mcp==2.2.0` is unavailable through the approved Microsoft package
proxy. [support/runtime_check.py](support/runtime_check.py) rejects other SDK versions rather than
silently running SDK v1. SDK release numbers and MCP protocol dates are separate;
the client selects protocol mode `2026-07-28`.

## Start with two files

1. [client.py](client.py): SDK `OAuthClientProvider`, callback delivery and tool call.
2. [server.py](server.py): protected HTTP server, token verification and one Playwright tool.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the request flow. Supporting code is
separate so it does not obscure these two entry points:

| Folder | Purpose | Read when |
| --- | --- | --- |
| `support/` | [Authorization fixture](support/auth_server.py), [shared rules](support/auth_rules.py), and SDK version guard. | You want to understand the simulated identity service. |
| `lab/` | [Short demo](lab/demo.py) and [HTTP helpers](lab/lab_support.py), with no MCP dependency. | You want to try the issuer checks without installing SDK v2. |
| `tests/` | [Fixture and rule tests](tests/test_auth.py), using standard-library `unittest`. | You want to check PKCE, issuer, expiry and replay behavior. |

The real SDK path does not import `lab` or `tests`. The lab manually exercises
OAuth rules; it does **not** implement MCP or verify the SDK's OAuth implementation.
The local authorization fixture is needed because this introduction uses no
external identity provider. Its checks are teaching content, not a production framework.

## Run the stdlib lab now

Run all commands below from the **repository root** in PowerShell, using the
existing root virtual environment (Python 3.13+):

```powershell
Push-Location mcp_learning_samples/mcp_v2_oauth_local
..\..\.venv\Scripts\python.exe -m lab.demo
..\..\.venv\Scripts\python.exe -m unittest tests.test_auth -v
Pop-Location
```

No installation is needed. Temporary loopback servers stop automatically.
The demo confirms a resource-bound token for `valid` (one token request), then
rejects `wrong-issuer` and `missing-issuer` (zero token requests each).
Tokens, authorization codes and PKCE verifiers are not printed.

## Manual real-SDK check: three terminals

**Blocked until the pinned SDK is available.** These are instructions, not a
record of a passing integration run. When approved packages become available,
prepare this sample's isolated environment, not the root environment:

```powershell
uv sync --directory mcp_learning_samples/mcp_v2_oauth_local --default-index https://packagefeedproxy.microsoft.io/pypi/simple/
uv run --directory mcp_learning_samples/mcp_v2_oauth_local playwright install chromium
```

[pyproject.toml](pyproject.toml) selects
`https://packagefeedproxy.microsoft.io/pypi/simple/`. Do not bypass the proxy,
disable TLS verification or substitute SDK v1. Chromium is a separate download
subject to organizational policy. Ports **8020** and **8021** must be free.

Open three terminals at the repository root:

```powershell
# Terminal 1: authorization fixture (leave running)
uv run --directory mcp_learning_samples/mcp_v2_oauth_local python -m support.auth_server

# Terminal 2: protected MCP server (leave running)
uv run --directory mcp_learning_samples/mcp_v2_oauth_local python server.py

# Terminal 3: client, then inspect the fixture's token-request counter
uv run --directory mcp_learning_samples/mcp_v2_oauth_local python client.py
Invoke-RestMethod http://127.0.0.1:8020/stats
```

Expected positive result: `WITHOUT TOKEN: 401`, `AUTHENTICATED TOOLS` containing
`read_demo_page`, and `PAGE` with title `Authenticated browser demo`.
The client exits successfully and `token_requests` is **1** after one run.
The tool reads HTML created locally in Chromium; it does not fetch a website.

For each negative check, stop **only Terminal 1** with Ctrl+C and restart it
using one of these commands (run them separately):

```powershell
uv run --directory mcp_learning_samples/mcp_v2_oauth_local python -m support.auth_server --scenario wrong-issuer
uv run --directory mcp_learning_samples/mcp_v2_oauth_local python -m support.auth_server --scenario missing-issuer
```

After each restart, rerun **both Terminal 3 commands**. Each new client process
starts with empty credential storage; restarting the fixture resets its counter.
Expected: `WITHOUT TOKEN: 401`, then `SIMULATED LOGIN`, then an issuer-validation
error and a nonzero client exit, no authenticated tool/page output, and
`token_requests` **0**. A dependency error, connection failure or failure before
the callback is **not** a passing negative check. Stop both servers with Ctrl+C
when finished. There is no subprocess supervisor.

## Boundaries and specifications

This is loopback-only teaching code, not a production identity service. Login
and consent are auto-approved. The client captures the HTTP 302 callback without
following it: **nothing listens on 8022**. HTTP, unauthenticated introspection and
in-memory storage are deliberate fixture limitations; TLS, real login/consent,
refresh, revocation and production deployment are outside scope.

- [MCP authorization (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization): discovery and protected-resource authorization.
- [RFC 9207](https://www.rfc-editor.org/rfc/rfc9207): callback `iss` identifies the authorization server.
- [RFC 7636](https://www.rfc-editor.org/rfc/rfc7636): PKCE binds a code to its initiating client.
- [RFC 8707](https://www.rfc-editor.org/rfc/rfc8707): `resource` identifies the intended token recipient.
- [SDK OAuth client](https://py.sdk.modelcontextprotocol.io/client/oauth-clients/) and [auth migration](https://py.sdk.modelcontextprotocol.io/migration/#oauth-and-server-auth): SDK wiring and callback shape.