# MCP in Practice: Web Browsing, Protocols, and Apps

A Playwright browsing application with Azure OpenAI/OpenAI, plus focused examples
of MCP v1/v2, OAuth, and interactive MCP Apps.

1. [Original browsing application](#1-original-browsing-application) — Azure OpenAI/OpenAI integration, setup and client connections.
2. [MCP v1 and v2 samples](#2-mcp-v1-and-v2-samples) — browser tools and local OAuth flows.
3. [MCP Apps samples](#3-mcp-apps-samples) — interactive tool-response UIs built with Prefab.

## 1. Original browsing application

- A minimal server/client application implementation utilizing the Model Context Protocol (MCP) and Azure OpenAI.

    1. The MCP server is built with `FastMCP`.  
    2. `Playwright` is an an open source, end to end testing framework by Microsoft for testing your modern web applications. 
    3. The MCP response about tools will be converted to the OpenAI function calling format.  
    4. The bridge that converts the MCP server response to the OpenAI function calling format customises the `MCP-LLM Bridge` implementation.
    5. To ensure a stable connection, the server object is passed directly into the bridge. 
    6. The `client_bridge` supports both in-process and external (stdio) MCP server connections, enabling reuse by different clients (e.g., Claude Code, VS Code, custom scripts).

### Setup and run

During the development phase in December 2024, the Python project should be initiated with 'uv'. Other dependency management libraries, such as 'pip' and 'poetry', are not yet fully supported by the MCP CLI.

1. Rename `.env.template` to `.env`, then fill in the values in `.env` for Azure OpenAI:

    ```bash
    AZURE_OPEN_AI_ENDPOINT=
    AZURE_OPEN_AI_API_KEY=
    AZURE_OPEN_AI_DEPLOYMENT_MODEL=
    AZURE_OPEN_AI_API_VERSION=
    ```

1. Install `uv` for python library management

    ```bash
    pip install uv
    uv sync
    ```

1. Execute `python chatgui.py`

    - The sample screen shows the client launching a browser to navigate to the URL.

    <img alt="chatgui" src="docs/chatgui_gpt_generate.png" width="300"/>

#### Azure v1 endpoint and model parameters

For an endpoint ending in `/openai/v1`, set `AZURE_OPEN_AI_ENDPOINT` to the full
URL and `AZURE_OPEN_AI_DEPLOYMENT_MODEL` to an existing deployment name. This
path uses the OpenAI-compatible client and does not require an API version.
Use `AZURE_OPEN_AI_API_KEY`, or supply a short-lived Entra token through the
process environment variable `AZURE_OPENAI_AD_TOKEN` when the key is unset.
Tokens are not refreshed automatically; renew them before launching and never
commit them to a file.

Request parameters are configured explicitly, not inferred from model names:

- `OPENAI_TOKEN_LIMIT_PARAMETER` selects `max_tokens` or `max_completion_tokens`.
  The v1 default is `max_completion_tokens`; the legacy Azure default remains
  `max_tokens`. This chooses the request field for the `LLMConfig.max_tokens`
  budget, not a claim that every deployment supports it.
- `OPENAI_TEMPERATURE` optionally sets sampling temperature. The v1 path omits
  it by default so the deployment can use its own default. Legacy Azure retains
  `0.7`. In Python, set `LLMConfig.temperature=None` to omit it.
- Python callers can set `LLMConfig.token_limit_parameter` directly. Configure
  parameters for the selected deployment; arbitrary deployment names and new
  model generations require no model-prefix changes in the bridge.

### Using with External Clients

The MCP server can be used by external clients (Claude Desktop, VS Code, Claude Code, etc.) via `mcp.json` configuration.

#### Claude Desktop / Claude Code

Add to your `claude_desktop_config.json` (Claude Desktop) or `.claude/mcp.json` (Claude Code):

```json
{
  "mcpServers": {
    "browser-navigator": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "./server/browser_navigator_server.py:app"],
      "cwd": "/path/to/mcp-aoai-web-browsing",
      "env": {
        "AZURE_OPEN_AI_ENDPOINT": "...",
        "AZURE_OPEN_AI_API_KEY": "...",
        "AZURE_OPEN_AI_DEPLOYMENT_MODEL": "...",
        "AZURE_OPEN_AI_API_VERSION": "..."
      }
    }
  }
}
```

#### VS Code

Add to `.vscode/mcp.json` in your workspace:

```json
{
  "servers": {
    "browser-navigator": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "./server/browser_navigator_server.py:app"],
      "cwd": "${workspaceFolder}",
      "env": {
        "AZURE_OPEN_AI_ENDPOINT": "...",
        "AZURE_OPEN_AI_API_KEY": "...",
        "AZURE_OPEN_AI_DEPLOYMENT_MODEL": "...",
        "AZURE_OPEN_AI_API_VERSION": "..."
      }
    }
  }
}
```

### Using the Bridge Programmatically

#### Connecting over stdio

The `client_bridge` also supports connecting to external MCP servers via stdio from Python:

```python
from client_bridge import BridgeConfig, MCPServerConfig, BridgeManager
from client_bridge.llm_config import get_default_llm_config

config = BridgeConfig(
    server_config=MCPServerConfig(
        command="uv",
        args=["run", "fastmcp", "run", "./server/browser_navigator_server.py:app"],
    ),
    llm_config=get_default_llm_config(),
    system_prompt="You are a helpful assistant.",
)

async with BridgeManager(config) as bridge:
    response = await bridge.process_message("Navigate to https://example.com")
```

#### Using Standard OpenAI (non-Azure)

```python
from client_bridge.llm_config import get_openai_llm_config

config = BridgeConfig(
    mcp=server,
    llm_config=get_openai_llm_config(),
)
```

Set environment variables:

```bash
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-...
```

#### Direct Tool Execution

For clients that manage their own LLM loop, the bridge exposes tool metadata and direct execution:

```python
async with BridgeManager(config) as bridge:
    tools = bridge.get_tools()  # OpenAI function calling format
    result = await bridge.execute_tool("playwright_navigate", {"url": "https://example.com"})
```

<a id="learning-samples"></a>

## 2. MCP v1 and v2 samples

Independent introductory examples, separate from the original application above.
Each folder has its own dependencies; use its README's directory-scoped commands
from the repository root rather than upgrading the root environment. No LLM API
key is needed for these samples.

| Sample | What it demonstrates |
| --- | --- |
| [MCP v1 — Browser tools](mcp_learning_samples/mcp_v1_browser_tools/README.md) | Read a page or capture a screenshot with Playwright; observe explicit MCP initialization and session handling over HTTP. |
| [MCP v2 — Browser tools](mcp_learning_samples/mcp_v2_browser_tools/README.md) | The same browser operations with explicitly selected newer protocol mode; integration remains blocked and unverified. |
| [MCP v2 — Local OAuth](mcp_learning_samples/mcp_v2_oauth_local/README.md) | Obtain a token before calling a protected browser tool; explore issuer validation and PKCE with a local authorization fixture. Includes an SDK-independent lab; real SDK integration remains unverified. |

### Specification references

The MCP v1/v2 examples below concern protocol behavior, not SDK version labels.
The dated references identify the exact specifications targeted by these samples:

- **Core MCP 2025-11-25** defines client/server communication, including
  [initialization and version negotiation](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle).
  The browser sample calls `initialize()` rather than hard-coding a protocol date.
  With the installed, pinned `mcp==1.27.0`, the latest supported version is
  `2025-11-25`, and negotiation to that version has been confirmed at runtime.
- **Core MCP 2026-07-28** is the
  [core specification](https://modelcontextprotocol.io/specification/2026-07-28)
  targeted by the newer browser and OAuth samples. Their clients explicitly set
  `mode="2026-07-28"` rather than calling the earlier `initialize()` API. This is
  the intended protocol path in the code, not a verified integration result.

**Verification limit:** the core 2026-07-28 samples' SDK 2 integration remains
blocked and unverified end to end because the approved package proxy could not
resolve `mcp==2.2.0`. Passing the local OAuth lab does not verify SDK 2 integration.
These are teaching examples, not production deployment templates.

## 3. MCP Apps samples

MCP Apps add interactive UI resources and host-mediated interaction on top of
core MCP. They are an optional extension, not an SDK v2-only feature. These
independent samples need no LLM API key; follow each guide's setup commands.

| Sample | What it demonstrates |
| --- | --- |
| [Reactive reading card](mcp_learning_samples/apps_reactive/README.md) | Return a Prefab reading card whose input and reset actions update client-side state without further tool calls. |
| [Browser panel](mcp_learning_samples/apps_browser/README.md) | Use an interactive button to call a Playwright tool and display its page text and screenshot inside an Apps-capable host. |

### Specification and host requirements

The official [Apps overview](https://modelcontextprotocol.io/docs/extensions/apps)
links to the [2026-01-26 Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx).
These examples use FastMCP 3.2.0, Prefab 0.20.2 and MCP SDK 1.27.0. A compatible
host is required for embedded UI and tool callbacks; standalone previews are not
full host integration tests.

### Sample screenshots

Standalone Prefab previews, not MCP chat-host captures. The browser result was
generated by a real local Playwright call and rendered separately.

<img alt="Reactive MCP App preview" src="docs/screenshots/apps-reactive.png" width="420"/>
<img alt="Local Playwright result preview" src="docs/screenshots/apps-browser-result.png" width="420"/>

See the Apps sample guides for the full images and preview limitations. No
screenshots are presented as evidence of the unverified SDK v2 integration.

## Protocol and tool notes

### stdio and JSON-RPC

`stdio` is a **transport layer** (raw data flow), while **JSON-RPC** is an **application protocol** (structured communication). They are distinct but often used interchangeably, e.g., "JSON-RPC over stdio" in protocols.

### Tool description

```cmd
@self.mcp.tool()
async def playwright_navigate(url: str, timeout=30000, wait_until="load"):
    """Navigate to a URL.""" -> This comment provides a description, which may be used in a mechanism similar to function calling in LLMs.

# Output
Tool(name='playwright_navigate', description='Navigate to a URL.', inputSchema={'properties': {'url': {'title': 'Url', 'type': 'string'}, 'timeout': {'default': 30000, 'title': 'timeout', 'type': 'string'}
```

## References

### Model Context Protocol (MCP)

**Model Context Protocol (MCP)** MCP (Model Context Protocol) is an open protocol that enables secure, controlled interactions between AI applications and local or remote resources. 

### Official Repositories

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)  
- [Create Python Server](https://github.com/modelcontextprotocol/create-python-server)  
- [MCP Servers](https://github.com/modelcontextprotocol/servers)  

### Related Projects

- [FastMCP](https://github.com/jlowin/fastmcp): The fast, Pythonic way to build MCP servers.
- [Chat MCP](https://github.com/daodao97/chatmcp): MCP client
- [MCP-LLM Bridge](https://github.com/bartolli/mcp-llm-bridge): MCP implementation that enables communication between MCP servers and OpenAI-compatible LLMs

### MCP Playwright

- [MCP Playwright server](https://github.com/executeautomation/mcp-playwright)  
- [Microsoft Playwright for Python](https://github.com/microsoft/playwright-python)  

### Community Resources

- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)  
- [MCP on Reddit](https://www.reddit.com/r/mcp/)  

## Development tips

### uv commands

- [features](https://docs.astral.sh/uv/getting-started/features)

```
uv run: Run a script.
uv venv: Create a new virtual environment. By default, '.venv'.
uv add: Add a dependency to a script
uv remove: Remove a dependency from a script
uv sync: Sync (Install) the project's dependencies with the environment.
```

### Process cleanup and debugging

- taskkill command for python.exe

```cmd
taskkill /IM python.exe /F
```
- Visual Code: Python Debugger: Debugging with launch.json will start the debugger using the configuration from .vscode/launch.json.

<!-- ### Sample query

Navigate to website http://eaapp.somee.com and click the login link. In the login page, enter the username and password as "admin" and "password" respectively and perform login. Then click the Employee List page and click "Create New" button and enter realistic employee details to create for Name, Salary, DurationWorked, Select dropdown for Grade as CLevel and Email. -->

