- Removed duplicated get_plugin_catalog in app/api/plugins.py.
- Fixed duplicated required_role field in PluginUpdate model.
- Cleaned up redundant logic and double commit in update_plugin function.

## Schema-Driven Edit UX Implementation (Feb 27, 2026)

- **Dynamic Schema Fetching**: Successfully implemented fetching schema from `/plugins/{id}/schema` in `EditPluginButton`. This allows for a much better UX than raw JSON editing for plugins that define their configuration schema.
- **Secret Handling**: Adopted the pattern of leaving password fields empty by default during edits. A placeholder "•••••••• (unchanged unless filled)" informs the user that their existing secret is safe and won't be overwritten unless they provide a new value.
- **Form State Management**: Used a dedicated `installFormValues` state to track dynamic inputs, separate from the primary plugin metadata (name, type, etc.).
- **Consistency**: Matched the styling of `PluginForm.tsx` to ensure a cohesive look and feel across the integrations dashboard.
- **Fallback**: Maintained the JSON textarea fallback for custom plugins or those without a schema, ensuring no loss of existing functionality.
- **Action Updates**: Updated `updatePlugin` server action to explicitly support `secrets`, bridging the gap between frontend UX and backend capabilities.
### Integration of ViewSkillButton
- Integrated `ViewSkillButton` into the `IntegrationsPage` table actions.
- Fixed a missing import for `Info` in `ViewSkillButton.tsx` that was causing build failures during `dev_check.sh`.
- Order of actions: View Skill -> Edit -> Delete.
