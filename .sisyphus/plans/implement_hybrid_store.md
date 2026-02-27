# Work Plan: Hybrid Plugin Store Architecture (Execution Phase)

## Objective
Convert the current free-form URL plugin registration system into a "Hybrid Store". This will provide a curated "App Store" experience using a static JSON manifest, while retaining a "Custom" tab for advanced users. This solves the issue where plugins were missing critical metadata (`required_role`, `allowed_hostnames`).

## Pre-requisites Completed
- `plugin_catalog.json` has been created.
- `app/models/plugin.py` has been updated with `manifest_id` and `required_role`.
- Alembic migration `hybrid_store` has been generated and applied.
- `app/core/mcp_manager.py` has been updated to merge catalog metadata and inject `ALLOWED_SSE_HOSTNAMES`.

## Remaining Implementation Steps

- [x] Task 1: Update Plugins API

**File**: `app/api/plugins.py`
**Actions**:
1. Add `import os` and `import json` at the top.
2. Update `PluginCreate` schema:
   - Add `manifest_id: Optional[str] = None`
   - Add `required_role: str = "user"`
3. Update `PluginUpdate` schema:
   - Add `manifest_id: Optional[str] = None`
   - Add `required_role: Optional[str] = None`
4. Add the Catalog Endpoint **BEFORE** `GET /{plugin_id}`:
```python
@router.get("/catalog")
async def get_plugin_catalog(current_user: User = Depends(require_admin)):
    """Get the predefined plugin catalog (App Store)."""
    catalog_path = os.path.join(os.getcwd(), "plugin_catalog.json")
    try:
        if not os.path.exists(catalog_path):
            return []
        with open(catalog_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read plugin catalog: {e}")
        raise HTTPException(status_code=500, detail="Failed to load plugin catalog")
```

- [x] Task 2: Update Frontend Server Actions

**File**: `web/src/app/actions/plugins.ts`
**Actions**:
1. Update `CreatePluginData` interface to include `manifest_id?: string` and `required_role?: string`.
2. Ensure the fetch POST body passes these new fields.

- [x] Task 3: Overhaul PluginForm Component

**File**: `web/src/app/integrations/PluginForm.tsx`
**Actions**:
1. Implement a state for tabs: `const [activeTab, setActiveTab] = useState<"store" | "custom">("store");`
2. Fetch the catalog data from `/plugins/catalog` on mount.
3. **Store Tab**: Render a grid of cards for each catalog item. Add an "Install" button that calls `createPlugin` with the item's predefined values.
4. **Custom Tab**: Render the existing form, but add a `required_role` select dropdown ("user", "admin", "guest") alongside the Type and Status fields.

- [x] Task 4: Quality Assurance

**Actions**:
1. Run `bash scripts/dev_check.sh` to ensure Python syntax, Ruff formatting, and Frontend builds are successful.

## Final Verification Wave
- [x] Manual QA: Navigate to `/integrations`. Verify the "Plugin Store" tab shows Home Assistant and Lark. Verify clicking install works.

- [x] Confirm `dev_check.sh` passes 100%.
