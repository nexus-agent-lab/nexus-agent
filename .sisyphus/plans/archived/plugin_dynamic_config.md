# Implementation Plan: Manifest Form Builder & Plugin-Skill Bundling

## Phase 1: Catalog Expansion [COMPLETED]

**Target File**: `plugin_catalog.json`

- Update the existing plugin entries (e.g., HomeAssistant) to include the new configuration structures.
- **`env_schema`**: Define configuration keys (e.g., `HA_TOKEN`) required by the plugin. Each key should specify its `type` (e.g., `text`, `password`, `url`), UI `label`, and `required` boolean.
- **`bundled_skills`**: Add an array (e.g., `["homeassistant"]`) to associate specific skills with the plugin installation.

## Phase 2: Backend API Evolution [COMPLETED]

**Target File**: `app/api/plugins.py`

- Modify the API endpoints to handle dynamic configuration, secrets, and automated skill installation.
- Enhance the `PluginCreate` Pydantic schema to accept `secrets: Optional[Dict[str, str]] = None`.
- In the `create_plugin()` endpoint:
  1. Create the `Plugin` database row.
  2. Iterate over the provided `secrets` payload.
  3. Create encrypted `Secret` rows tied to the new `plugin_id` with `scope="global"`.
  4. After successful plugin creation, check the catalog's `bundled_skills` using the associated `manifest_id`.
  5. Iterate over any defined `bundled_skills` and trigger `SkillLoader.install_skill()` to automatically provision them.

## Phase 3: Frontend Dynamic UI [COMPLETED]

**Target File**: `web/src/app/integrations/PluginForm.tsx`

- Enhance the UI to dynamically generate configuration forms based on the `env_schema`.
- Introduce an **Install Configuration Modal** that appears when a user clicks "Install" on a plugin.
- If the selected `item.env_schema` exists, dynamically render input fields inside the modal. Use the schema's `type` field to determine the input field type (e.g., `password` for sensitive tokens, `text` for standard config, `url` for endpoint addresses).
- Collect the user input and separate it into two distinct payload buckets: 
  - `config`: For non-sensitive fields.
  - `secrets`: For `password`/token fields.
- Submit the combined payload to the newly updated backend API structure.

## Phase 4: Quality Assurance [COMPLETED]

**Action**: Run Development Checks

- Execute the `dev_check.sh` script to validate all modifications.
- **Command**: `bash scripts/dev_check.sh`
- Ensure all static analysis (Ruff) and unit tests (Pytest) pass successfully prior to committing any implementation changes.