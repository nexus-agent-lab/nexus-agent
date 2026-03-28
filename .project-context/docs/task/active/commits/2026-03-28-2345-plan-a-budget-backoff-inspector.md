# Checkpoint

## Intent
Implement the Plan A stabilization path for browser-heavy research flows: 429 slow backoff, token-aware large-output guidance, token-budget compact gating, read-only inspector tools, and session-scoped workspace lifecycle fixes.

## Previous Context
- Browser MCP connectivity and skill routing anchor work had already been repaired.
- The user approved Plan A as the immediate stabilization direction for browser-result handling and context-budget behavior.
- Most of the implementation had already landed in the working tree, but final validation and a remaining sandbox/session-workspace gap still needed to be closed.

## Changes Made
- Confirmed and retained the new LLM budget / retry path across:
  - [app/core/llm_utils.py](/Users/michael/work/nexus-agent/app/core/llm_utils.py)
  - [app/core/agent.py](/Users/michael/work/nexus-agent/app/core/agent.py)
  - [app/core/intent_gate.py](/Users/michael/work/nexus-agent/app/core/intent_gate.py)
  - [app/core/memory.py](/Users/michael/work/nexus-agent/app/core/memory.py)
  - [app/core/skill_generator.py](/Users/michael/work/nexus-agent/app/core/skill_generator.py)
  - [app/core/session.py](/Users/michael/work/nexus-agent/app/core/session.py)
- Kept the new read-only inspector tool group and worker-aware routing in place:
  - [app/tools/inspector_tools.py](/Users/michael/work/nexus-agent/app/tools/inspector_tools.py)
  - [app/tools/registry.py](/Users/michael/work/nexus-agent/app/tools/registry.py)
  - [app/core/tool_catalog.py](/Users/michael/work/nexus-agent/app/core/tool_catalog.py)
- Closed the session workspace lifecycle gap:
  - `clear_history()` now deletes session messages, summaries, and workspace artifacts
  - added TTL cleanup helpers plus [scripts/admin/cleanup_session_workspaces.py](/Users/michael/work/nexus-agent/scripts/admin/cleanup_session_workspaces.py)
- Fixed the sandbox runtime bug in [app/tools/sandbox.py](/Users/michael/work/nexus-agent/app/tools/sandbox.py):
  - the embedded audit prelude now receives a concrete `SANDBOX_DATA_DIR` value safely
  - avoids Python-format interpolation colliding with f-string braces inside the prelude
- Added focused test coverage:
  - [tests/unit/test_llm_utils_budget.py](/Users/michael/work/nexus-agent/tests/unit/test_llm_utils_budget.py)
  - [tests/unit/test_session_budget_compact.py](/Users/michael/work/nexus-agent/tests/unit/test_session_budget_compact.py)
  - [tests/unit/test_inspector_tools.py](/Users/michael/work/nexus-agent/tests/unit/test_inspector_tools.py)
  - [tests/unit/test_session_workspace_cleanup.py](/Users/michael/work/nexus-agent/tests/unit/test_session_workspace_cleanup.py)
  - [tests/unit/test_sandbox_session_workspace.py](/Users/michael/work/nexus-agent/tests/unit/test_sandbox_session_workspace.py)
  - [tests/unit/test_tool_catalog.py](/Users/michael/work/nexus-agent/tests/unit/test_tool_catalog.py)

## Decisions
- Treated Plan A as a stabilization layer, not a full browser-session productization effort.
- Kept `python_sandbox` available in general, but moved browser-result handling away from the old “large result => always use python” bias.
- Used session-scoped workspaces as the shared boundary for browser offloads, inspector reads, and sandbox post-processing so per-user/per-session isolation stays consistent.
- Added TTL cleanup as a manual admin path first, rather than committing immediately to an automatic scheduler policy.

## Verification
- `uv run ruff check app/core/llm_utils.py app/core/agent.py app/core/session.py app/tools/session_workspace.py app/tools/inspector_tools.py app/tools/sandbox.py app/core/tool_catalog.py app/tools/registry.py scripts/admin/cleanup_session_workspaces.py tests/unit/test_llm_utils_budget.py tests/unit/test_session_budget_compact.py tests/unit/test_inspector_tools.py tests/unit/test_session_workspace_cleanup.py tests/unit/test_sandbox_session_workspace.py tests/unit/test_tool_catalog.py`
  - passed
- `uv run pytest tests/unit/test_sandbox_session_workspace.py tests/unit/test_llm_utils_budget.py tests/unit/test_session_budget_compact.py tests/unit/test_inspector_tools.py tests/unit/test_session_workspace_cleanup.py tests/unit/test_tool_catalog.py`
  - `21 passed`
