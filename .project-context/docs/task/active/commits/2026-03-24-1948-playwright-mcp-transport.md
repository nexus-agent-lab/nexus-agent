# Commit: 2026-03-24-1948-playwright-mcp-transport

## Intent
Repair the Web Browser MCP path so the Playwright toolset actually registers into the agent, instead of failing MCP connection and falling back to `python_sandbox`.

## Previous Context
- `plugin_catalog.json` still pointed Web Browser at `http://mcp-playwright:3000/sse`.
- `app/core/mcp_manager.py` only used `sse_client(...)` for remote MCP URLs.
- `mcp-playwright` logs advertised `http://localhost:3000/mcp` as the recommended client endpoint and described `/sse` as legacy transport.
- Direct probing from `nexus-app` showed `http://mcp-playwright:3000/mcp` initially failed with `403 Access is only allowed at localhost:3000`, revealing an additional host-check mismatch for container-to-container requests.

## Changes Made
- **File**: `app/core/mcp_manager.py`
  - Logic: Added streamable HTTP MCP support via `mcp.client.streamable_http.streamablehttp_client` for URLs ending in `/mcp`.
  - Logic: Kept legacy SSE support for existing `/sse` endpoints.
  - Logic: Added normalized remote `Host` header injection so service-name URLs such as `http://mcp-playwright:3000/mcp` are accepted by the current Playwright MCP host allowlist.
- **File**: `plugin_catalog.json`
  - Logic: Updated the official Playwright plugin endpoint from `/sse` to `/mcp`.
- **File**: `docker-compose.yml`
  - Logic: Added `--allowed-hosts mcp-playwright,localhost,127.0.0.1` to the Playwright MCP server startup.
  - Logic: Switched the requested browser from default `chrome` to `chromium`.
  - Logic: Began moving the service image from `node:20-slim` to `mcr.microsoft.com/playwright:v1.52.0-noble` to satisfy missing browser runtime libraries.
- **File**: `skills/web_browsing.md`
  - Logic: Replaced stale required tool names with the actual registered Playwright tools (`browser_snapshot`, `browser_take_screenshot`).
  - Logic: Updated examples and guidance to reflect the snapshot-based extraction pattern used by the real Playwright MCP toolset.

## Decisions
- Chose to support both `/sse` and `/mcp` in the connection layer instead of forcing every MCP server back onto legacy SSE.
- Kept the host-check workaround inside the Nexus connection layer because Playwright MCP currently rejects container DNS names when the HTTP `Host` header includes the port.
- Treated tool-name alignment in `skills/web_browsing.md` as part of the same fix, because once registration succeeded the old skill metadata would still have caused “tool not found” warnings.
- Continued one step past registration into browser-runtime validation, because tool registration alone was not enough to prove browser tasks would actually execute.

## Verification
- Verified inside `nexus-app` that the installed MCP SDK exposes both:
  - `mcp.client.sse.sse_client`
  - `mcp.client.streamable_http.streamablehttp_client`
- Verified direct Playwright MCP handshake success using `/mcp`:
  - `POST http://mcp-playwright:3000/mcp` with normalized `Host` header returned a valid MCP `initialize` response.
- Verified real tool discovery from Playwright MCP:
  - server identified itself as `Playwright 0.0.68`
  - listed 22 browser tools including `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, and `browser_wait_for`
- Verified `MCPManager.reload()` after the code change:
  - `Connected to Web Browser. Loaded 22 tools.`
  - registered sessions included `Home Assistant` and `Web Browser`
- Verified runtime smoke-test progress:
  - `browser_install` succeeded after switching to `chromium`
  - browser navigation still failed under the current `node:20-slim` container because required system libraries were missing
  - began pulling `mcr.microsoft.com/playwright:v1.52.0-noble` as the browser-ready runtime image, but the large image download was still in progress at session end

## Risks / Next Steps
- The connection-layer fix is complete, but the browser runtime still needs a browser-ready image or equivalent system dependencies before end-to-end browsing succeeds.
- The active `docker compose up -d mcp-playwright` run may still be pulling the official Playwright image after this session.
- After the image/runtime settles, rerun the minimal Weibo hot-search smoke test and then validate that the agent selects the registered browser tools in a normal user query path.
