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
**Goal**: Replace the local subprocess Python execution with a dedicated, network-isolated Docker container.
**Tasks**:
- [ ] Create `Dockerfile.sandbox`: Minimal Python 3.10 image with data science libraries (pandas, requests, bs4) but running as a non-root `sandbox` user.
- [ ] Create `app/sandbox_server.py`: A lightweight FastAPI server running inside the sandbox that accepts code, runs it with `asyncio.create_subprocess_exec` (with strict timeouts and memory limits), and returns stdout/stderr.
- [ ] Modify `docker-compose.yml`: Add `nexus-sandbox` service with strict limits (`read_only: true`, `tmpfs`, `networks: [sandbox-internal]`).
- [ ] Refactor `app/tools/sandbox.py`: Update the `PythonSandboxTool` to forward code execution via HTTP to `http://nexus-sandbox:9090/execute`. Maintain a local fallback for dev mode.

## Phase 3: The Code Factory (Self-Programming Loop)
**Goal**: Allow the agent to write, test, and persist its own tools.
**Tasks**:
- [ ] Create `app/models/internal_plugin.py`: Define an `InternalPlugin` SQLModel to store agent-generated code.
- [ ] Run Migrations: Generate and run Alembic migrations for the new table.
- [ ] Modify `app/tools/learning_tools.py`: Create the `save_internal_plugin` tool. It must verify the agent provides successful `test_output` from the sandbox before saving.
- [ ] Modify `app/tools/registry.py`: Expose the new tool.
- [ ] Modify `app/core/agent.py`: Add Rule 9 to `BASE_SYSTEM_PROMPT` instructing the agent on the "Write -> Test in Sandbox -> Save" loop.
