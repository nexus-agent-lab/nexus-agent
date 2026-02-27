- Updated plugin_catalog.json with env_schema and bundled_skills for Home Assistant and Lark.
- The env_schema includes type, label, and required fields as per the implementation plan.
- `PluginCreate` schema updated to include optional `secrets: Dict[str, str]` field.
- `create_plugin` API logic creates `Secret` records with `SecretScope.global_scope` and encrypts values using `encrypt_secret`.
- Evaluated `plugin_catalog.json` during plugin creation to automatically invoke `SkillLoader.install_skill` for defined `bundled_skills`.
## 2026-02-27 - Plugin Dynamic Configuration Overhaul

- Overhauled `PluginForm.tsx` to support dynamic installation configuration via modals.
- Implemented `env_schema` parsing from `plugin_catalog.json`.
- Added logic to split sensitive fields (type 'password') into `secrets` and other fields into `config`.
- Updated `createPlugin` server action to accept `secrets` object.
- Verified that the frontend build and backend tests pass after changes.
