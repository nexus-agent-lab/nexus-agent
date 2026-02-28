# Work Plan: Fix Plugin RBAC Linkage (Role-Based Access Control)

## Objective
Currently, even if a plugin is registered with `required_role="user"`, a standard user still gets a "Permission Denied" error because the `AuthService` only checks the user's explicit `allow_domains` whitelist. This plan links the Plugin's `required_role` to the execution-time permission check, allowing a "Global Plugin" behavior.

## Scope
- **IN**: Update `app/core/auth_service.py` to include role-level comparison logic.
- **IN**: Update `app/core/agent.py` to pass the plugin's `required_role` from metadata to the permission check.
- **IN**: Update `app/core/mcp_manager.py` to ensure every loaded tool carries its plugin's `required_role` in its metadata.

## Implementation Steps

### Task 1: Define Role Levels in AuthService
**File**: `app/core/auth_service.py`
**Actions**:
1. Add a `ROLE_LEVELS` constant: `{"admin": 100, "user": 50, "guest": 10}`.
2. Update `check_tool_permission` signature to accept `required_role: str = None`.
3. Inside the method, if `required_role` is provided, compare `ROLE_LEVELS[user.role]` against `ROLE_LEVELS[required_role]`. If the user's level is high enough, return `True` immediately.

### Task 2: Inject required_role into Tool Metadata
**File**: `app/core/mcp_manager.py`
**Actions**:
1. In `_create_mcp_tool`, ensure the generated `BaseTool` has `required_role` in its `metadata` dictionary, pulled from the plugin's configuration.

### Task 3: Use required_role in Agent Permission Check
**File**: `app/core/agent.py`
**Actions**:
1. In `tool_node_with_permissions`, extract `required_role` from `tool_to_call.metadata`.
2. Pass it as the third argument to `AuthService.check_tool_permission`.

### Task 4: Quality Assurance
- Run `bash scripts/dev_check.sh`.
- Specifically verify that `michael` (user role) can now call `list_entities` if the plugin is set to `"user"` role.

## Final Verification
- [ ] Log shows "michael" successfully executing tools from the Home Assistant domain.
- [ ] No more "Permission Denied" for tools where the user meets the role requirement.
