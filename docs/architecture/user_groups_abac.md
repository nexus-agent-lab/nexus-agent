# Implementation Plan: User Groups as JSON Tags (ABAC)

- [x] Phase 1: Database Schema Migration

- Modify `app/models/user.py`: Add `groups: List[str] = Field(default=["default"], sa_column=Column(JSON))` (ensure `Column` and `JSON` from `sqlalchemy` are imported).
- Modify `app/models/plugin.py`: Add `allowed_groups: List[str] = Field(default=[], sa_column=Column(JSON))` (import `Column`, `JSON` from `sqlalchemy`).
- Run `bash scripts/admin/new_migration.sh "add_groups"` and then `bash scripts/admin/upgrade_db.sh`.

- [x] Phase 2: Core Authentication Logic

- Clean up `app/core/auth_service.py`: Remove duplicate `check_tool_permission` methods.
- Update `check_tool_permission` to accept `allowed_groups: List[str] = None`.
- Implement the "Horizontal Gate" logic: if `allowed_groups` is not empty, check if `set(user.groups).intersection(set(allowed_groups))` is true.

- [x] Phase 3: MCP & Agent Integration

- Update `app/core/mcp_manager.py`: When loading plugins, extract `allowed_groups` from `plugin_catalog.json` (or DB) and inject it into the `metadata` dictionary created in `_convert_to_langchain_tool` -> `StructuredTool.from_function`.
- Update `app/core/agent.py`: In `tool_node_with_permissions`, extract `allowed_groups = tool_to_call.metadata.get("allowed_groups")` and pass it to `check_tool_permission`.

- [x] Phase 4: API & Frontend Updates

- [x] Update `app/api/users.py` and `app/api/plugins.py`: Ensure schemas (`UserUpdate`, `PluginCreate`, `PluginUpdate`) accept `groups` and `allowed_groups` respectively.

- [x] Update `web/src/app/users/[user_id]/EditUserForm.tsx` to include an input for `groups` (e.g. comma separated string converted to array).

- [x] Update `web/src/app/integrations/EditPluginButton.tsx` and `PluginForm.tsx` to include an input for `allowed_groups`.


- [x] Phase 5: Quality Assurance

- [x] Run `bash scripts/dev_check.sh`.
