# Work Plan: Fix Empty Plugin Store (Auth Header Omission)

## Objective
Fix the issue where the "Plugin Store" tab in the Integrations page appears empty. The root cause is a silent 401 Unauthorized failure because the frontend `fetchCatalog` function does not pass the required `X-API-Key` header to the backend.

## Scope
- **IN**: Update `web/src/app/integrations/page.tsx` to pass the `apiKey` to `PluginForm`.
- **IN**: Update `web/src/app/integrations/PluginForm.tsx` to accept the `apiKey` prop and inject it into the `fetchCatalog` request headers.
- **IN**: Prevent an infinite loading loop in `PluginForm.tsx` by tracking `catalogLoaded` state.
- **IN**: Harden the backend catalog path resolution in `app/api/plugins.py` so it works reliably in Docker.

## Implementation Steps

- [x] Task 1: Pass API Key from Parent Page

**File**: `web/src/app/integrations/page.tsx`
**Actions**:
1. Locate the `<PluginForm />` component invocation.
2. Update it to `<PluginForm apiKey={apiKey} />` (or whatever the payload api_key variable is named in that file, likely `payload.api_key as string`).

- [x] Task 2: Inject API Key into PluginForm Fetch

**File**: `web/src/app/integrations/PluginForm.tsx`
**Actions**:
1. Update `PluginFormProps` to require `apiKey: string`.
2. Destructure `apiKey` in the component signature.
3. In `fetchCatalog()`, add the `headers: { "X-API-Key": apiKey }` configuration.
4. Replace the `catalog.length === 0` dependency check in `useEffect` with a new `catalogLoaded` boolean state to prevent infinite re-fetching if the store is legitimately empty.

- [x] Task 3: Robust Backend Path Resolution

**File**: `app/api/plugins.py`
**Actions**:
1. In `get_plugin_catalog()`, replace `os.path.join(os.getcwd(), "plugin_catalog.json")` with a robust absolute path resolution based on the current file's location, e.g.:
```python
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
catalog_path = project_root / "plugin_catalog.json"
```

## Final Verification Wave
- [x] Manual QA: Navigate to `/integrations`. Verify the "Plugin Store" tab successfully fetches and displays the Home Assistant and Lark plugins.
- [x] Confirm `dev_check.sh` passes 100%.

- [ ] Confirm `dev_check.sh` passes 100%.