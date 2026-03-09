# Work Plan: Nexus Code Factory & Web Sandbox

## Objective
Upgrade Nexus Agent into an AI OS capable of autonomous web browsing and secure code execution/self-programming.

## Phase 1: Browser Integration (Quick Win)
**Goal**: Give the agent web capabilities using the official Playwright MCP.
**Tasks**:
- [ ] Modify `docker-compose.yml`: Add `mcp-playwright` service (using `ghcr.io/anthropics/mcp-playwright:latest` or fallback to node:20 npx run).
- [ ] Modify `plugin_catalog.json`: Add `official/playwright` entry with `context_tags: ["web", "browser", "search", "scrape"]` and required roles.
- [ ] Create `skills/web_browsing.md`: Write a skill card teaching the agent how to use `browser_navigate`, `browser_screenshot`, and extract text safely without exposing PII.

## Phase 2: The Fortress Sandbox (Medium)
**Goal**: Replace the local subprocess Python execution with a dedicated Docker container that is isolated from the Nexus app/runtime, with controllable network egress policies.
**Tasks**:
- [ ] Create `Dockerfile.sandbox`: Minimal Python 3.10 image with data science libraries (pandas, requests, bs4) but running as a non-root `sandbox` user.
- [ ] Create `app/sandbox_server.py`: A lightweight FastAPI server running inside the sandbox that accepts code, runs it with `asyncio.create_subprocess_exec` (with strict timeouts and memory limits), and returns stdout/stderr.
- [ ] Modify `docker-compose.yml`: Add `nexus-sandbox` service with strict limits (`read_only: true`, `tmpfs`, `networks: [sandbox-internal]`).
- [ ] Refactor `app/tools/sandbox.py`: Update the `PythonSandboxTool` to forward code execution via HTTP to `http://nexus-sandbox:9090/execute`. Maintain a local fallback for dev mode.

### Phase 2A: Safe Outbound Network Access
**Goal**: Allow `python_sandbox` to access the external internet when needed, without giving it access to the Nexus host, sibling containers, Docker socket, or internal service network.

**Security Requirements**:
- [ ] Sandbox must run only inside its own container. No host-process fallback in production.
- [ ] Sandbox must not mount the Docker socket, project workspace, or app source tree.
- [ ] Sandbox must not share the main internal service network used by `nexus-app`, `postgres`, `redis`, `mcp-homeassistant`, or `mcp-playwright`.
- [ ] Sandbox filesystem must remain ephemeral and constrained (`read_only`, `tmpfs`, bounded writable scratch dir).
- [ ] Sandbox must run as non-root with dropped Linux capabilities and `no-new-privileges`.

**Recommended Network Topology**:
- [ ] Put `nexus-sandbox` on two networks only:
  - `sandbox-control`: private internal bridge for `nexus-app -> nexus-sandbox` RPC
  - `sandbox-egress`: separate bridge/NAT path for outbound internet only
- [ ] Do not attach `nexus-sandbox` to the main app/service network.
- [ ] Block RFC1918/private ranges and Docker bridge subnets from inside the sandbox egress path to prevent lateral movement.
- [ ] Prefer outbound allow-by-policy for `80/443` only. No inbound ports except the control API from `nexus-app`.

**Execution Policy**:
- [ ] Add sandbox execution modes:
  - `offline`: current behavior, no internet
  - `egress_limited`: outbound HTTP/HTTPS allowed, internal addresses blocked
  - `egress_approved`: future mode for domain allowlists or per-task approval
- [ ] Default `python_sandbox` to `offline` unless the request explicitly needs web fetch/programmatic HTTP.
- [ ] Log mode, hostname targets, total bytes, and execution time for each run.
- [ ] Impose hard limits: CPU, memory, wall time, stdout/stderr size, response body size, and outbound request count.

**Runtime Guardrails**:
- [ ] Keep Python audit hooks, but move the main security boundary to container/network policy rather than relying on in-process Python hooks alone.
- [ ] Patch/monkeypatch socket resolution in sandbox mode only for better error messaging, but do not treat this as the security boundary.
- [ ] Disable access to known internal hostnames such as `postgres`, `redis`, `nexus-app`, `host.docker.internal`, `mcp-homeassistant`, and Docker bridge IPs.
- [ ] Sanitize environment variables passed into the sandbox; allow only a minimal whitelist.

**Why This Direction**:
- [ ] `web_browsing`/Playwright can fail or be unavailable.
- [ ] A network-enabled Python sandbox can still solve many practical tasks: scraping simple pages, calling HTTP APIs, parsing feeds, fetching JSON/CSV, and writing glue code.
- [ ] MCP JSON schemas are strict; a code sandbox is more flexible for recovery and adaptation, but only if the container boundary is stronger than the current in-process sandbox.

**Non-Goals / Explicit Rejections**:
- [ ] Do not allow host networking.
- [ ] Do not allow the sandbox to join the default compose network shared by core services.
- [ ] Do not allow unrestricted filesystem mounts from the Nexus workspace.
- [ ] Do not rely on prompt instructions as the primary security control.

**Suggested Rollout**:
- [ ] Step 1: Move sandbox to dedicated container with no network.
- [ ] Step 2: Add `egress_limited` mode with outbound-only internet and blocked internal ranges.
- [ ] Step 3: Add telemetry/audit for destinations, bytes, latency, and failures.
- [ ] Step 4: Evaluate whether domain allowlists or per-request approval are needed after real usage data.

## Phase 3: The Code Factory (Self-Programming Loop)
**Goal**: Allow the agent to write, test, and persist its own tools.
**Tasks**:
- [ ] Create `app/models/internal_plugin.py`: Define an `InternalPlugin` SQLModel to store agent-generated code.
- [ ] Run Migrations: Generate and run Alembic migrations for the new table.
- [ ] Modify `app/tools/learning_tools.py`: Create the `save_internal_plugin` tool. It must verify the agent provides successful `test_output` from the sandbox before saving.
- [ ] Modify `app/tools/registry.py`: Expose the new tool.
- [ ] Modify `app/core/agent.py`: Add Rule 9 to `BASE_SYSTEM_PROMPT` instructing the agent on the "Write -> Test in Sandbox -> Save" loop.
