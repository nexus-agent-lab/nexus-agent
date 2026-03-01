# Implementation Plan: Plugin Edit & Skill UX

## Phase 1: Backend API Extensions [COMPLETED]

**Target Files:** `app/api/plugins.py` (and relevant schema definitions)

1. **Schema Update:** Modify the `PluginUpdate` schema to accept an optional secrets dictionary: `secrets: Optional[Dict[str, str]] = None`.
2. **Update Logic:** In the `update_plugin()` route/service, implement logic to iterate over the `secrets` payload. For each key-value pair provided (where the value is not empty), upsert an encrypted `Secret` row in the database.
3. **Schema Endpoint:** Add a new endpoint `GET /plugins/{plugin_id}/schema`. This endpoint must:
   - Retrieve the plugin's `manifest_id` from the database.
   - Look up the manifest in `plugin_catalog.json`.
   - Return a JSON response containing `{ "env_schema": {...}, "bundled_skills": [...] }`.
4. **Skill Endpoint:** Add a new endpoint `GET /plugins/{plugin_id}/skill`. This endpoint must:
   - Use the catalog to find the bundled skill name for the given plugin.
   - Use `SkillLoader` to read the corresponding `.md` file content.
   - Return `{ "content": "..." }`.

## Phase 2: Edit Modal UI Overhaul [COMPLETED]

**Target File:** `web/src/app/integrations/EditPluginButton.tsx`

1. **Fetch Schema:** Upon opening the edit modal, trigger a fetch request to `GET /plugins/{id}/schema`.
2. **Dynamic Rendering:**
   - If an `env_schema` is returned, map over its fields to render dynamic input components (sharing logic with `PluginForm.tsx` where possible).
   - For fields defined as `password` (or similar secret types), render an empty input by default and set the placeholder to `••••••• (leave blank to keep unchanged)`.
3. **Payload Construction:** On submission, separate the form state into `config` and `secrets`. Only include secret keys in the `secrets` payload if the user explicitly typed a new value.
4. **Fallback:** If the API returns no `env_schema`, fall back to rendering the existing raw JSON textarea for configuration.

## Phase 3: View Skill Drawer UI [COMPLETED]

**Target Files:** `web/src/app/integrations/page.tsx` and/or a new `web/src/app/integrations/ViewSkillButton.tsx`

1. **Component Creation:** Create a "View Skill" button with a `BookOpen` icon, positioned adjacent to the existing Edit and Delete buttons for a plugin.
2. **Drawer/Modal UI:** Implement a side drawer or modal that triggers when the button is clicked.
3. **Fetch & Render:** Inside the drawer, fetch the skill content via `GET /plugins/{id}/skill`. Render the returned Markdown text using a markdown renderer component or a pre-formatted text block.

## Phase 4: Quality Assurance [COMPLETED]

**Target Action:** Local Verification

1. **Dev Check:** Run `bash scripts/dev_check.sh` to ensure Ruff linting, formatting, and Pytest suites pass with the new changes.
2. **Manual Security Verification:** Ensure that unchanged secrets are not accidentally overwritten with empty strings during a plugin update.
