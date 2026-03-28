# Checkpoint

## Intent
Close the session-workspace lifecycle gap by making session reset remove persisted workspace artifacts and by adding a TTL-based cleanup path for stale sandbox workspaces.

## Previous Context
- Session-scoped sandbox, inspector, and MCP large-output offload had already been implemented.
- Workspace files were stored under `SANDBOX_DATA_DIR/users/<user_id>/sessions/<session_id>/`.
- The user explicitly asked how those files were stored and whether they would be cleaned up.
- Review confirmed that `SessionManager.clear_history()` only deleted DB messages and did not remove workspace files or session summaries.

## Changes Made
- Updated [app/core/session.py](/Users/michael/work/nexus-agent/app/core/session.py) so `clear_history()` now:
  - deletes `SessionMessage` rows
  - deletes `SessionSummary` rows
  - deletes the current session workspace on disk when the session owner is known
- Extended [app/tools/session_workspace.py](/Users/michael/work/nexus-agent/app/tools/session_workspace.py) with:
  - `delete_session_workspace(...)`
  - `cleanup_stale_session_workspaces(...)`
  - stale detection based on the latest file/directory modification time inside each session workspace
- Added [scripts/admin/cleanup_session_workspaces.py](/Users/michael/work/nexus-agent/scripts/admin/cleanup_session_workspaces.py) as a dry-run-by-default admin script for TTL cleanup.
- Added focused coverage in [tests/unit/test_session_workspace_cleanup.py](/Users/michael/work/nexus-agent/tests/unit/test_session_workspace_cleanup.py).

## Decisions
- Reused the session workspace helper as the single lifecycle boundary instead of scattering cleanup logic across Telegram, MCP, and sandbox code paths.
- Kept TTL cleanup as a manual script first, because it solves the immediate accumulation problem without committing yet to a scheduler/cron policy.
- Expanded `clear_history()` to also remove `SessionSummary` rows so a “reset conversation” truly resets persisted context, not just raw messages.

## Verification
- `uv run ruff check app/core/session.py app/tools/session_workspace.py scripts/admin/cleanup_session_workspaces.py tests/unit/test_session_workspace_cleanup.py`
  - passed
- `uv run pytest tests/unit/test_session_workspace_cleanup.py tests/unit/test_inspector_tools.py tests/unit/test_session_budget_compact.py`
  - `5 passed`
