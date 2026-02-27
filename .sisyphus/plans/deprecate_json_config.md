# Work Plan: Deprecate JSON Config & Prevent Plugin Duplication

## Objective
The system is currently loading plugins from BOTH `mcp_server_config.json` AND the database `plugins` table, resulting in duplicate tools (e.g., `entity_action` appearing twice) and triggering `ROUTING AMBIGUITY` errors.
This plan entirely deprecates `mcp_server_config.json` from the runtime path, relying 100% on the Database as the single source of truth for installed plugins, while retaining the frontend's ability to pull blueprints from `plugin_catalog.json`.

## Scope
- **IN**: Modify `app/core/mcp_manager.py` to stop calling `_load_config()`.
- **IN**: Add URL deduplication logic in `_load_from_db()`.
- **IN**: Refactor `get_system_instructions()` to read from the DB plugins instead of the legacy JSON state.

## Implementation Steps

### Task 1: Update MCPManager Class State [COMPLETED]

**File**: `app/core/mcp_manager.py`
**Actions**:
1. Add `_db_plugins: Dict[str, Any] = {}` to the class attributes.

### Task 2: Implement Deduplication in DB Loader [COMPLETED]

**File**: `app/core/mcp_manager.py`
**Actions**:
1. At the end of `_load_from_db()` (around line 145), before returning, iterate through `servers.items()` and ensure no two plugins share the same `url`. If a duplicate is found, log a warning and delete it.
2. Save the final `servers` dict to `MCPManager._db_plugins = servers`.

### Task 3: Remove JSON Config from `initialize()` [COMPLETED]

**File**: `app/core/mcp_manager.py`
**Actions**:
1. In `initialize()`, remove the lines that call `self._load_config()` and merge logic.
2. It should simply be:
```python
db_servers = await self._load_from_db()
servers = db_servers if db_servers else {}
```

### Task 4: Fix System Instructions Dependency [COMPLETED]

**File**: `app/core/mcp_manager.py`
**Actions**:
1. Update `get_system_instructions()` to loop over `cls._db_plugins.items()` instead of `cls()._config.get("mcpServers", {}).items()`.

## Final Verification Wave
- [ ] Run `bash scripts/dev_check.sh` to ensure Python syntax and Pytest suites pass.
- [ ] Check `docker-compose logs nexus-app` to ensure the double-loading of Home Assistant tools is gone.