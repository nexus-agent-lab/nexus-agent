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

### Prompt Hardening for Quantized Models (2026-02-28)
- Updated BASE_SYSTEM_PROMPT in app/core/agent.py to include stronger anti-hallucination directives.
- Replaced "NO HALLUCINATION" rule with a "CRITICAL RULE" that explicitly forbids inventing tool names or arguments and instructs the model to STOP and ASK if unsure.
- Added a "SECURITY & ALIGNMENT" section to the system prompt to enforce RBAC compliance and prevent constraint bypassing.
- These changes aim to mitigate safety degradation and hallucination risks common in local quantized models as context grows.

### Roadmap Evolution for Quantization Safety (2026-02-28)
- Updated `docs/priorities.md` to include two new Epics focused on quantization safety hardening.
- Epic 1 (DualPath inspired) addresses tool output compaction to save KV-Cache and reduce context noise.
- Epic 2 (T-PTQ inspired) introduces a quantization-aware safety benchmark test suite.
- These updates provide a clear roadmap for architectural solutions to safety degradation in local quantized models.