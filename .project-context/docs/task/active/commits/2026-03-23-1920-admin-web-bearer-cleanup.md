# Commit: 2026-03-23-1920-admin-web-bearer-cleanup

## Intent
Find and fix similar legacy `X-API-Key` usage across JWT-backed admin web pages so signed-in admins do not hit inconsistent authentication failures.

## Previous Context
The admin audit wirelog toggle had already been fixed to use bearer auth. A follow-up search showed several other admin pages and client-side admin modals were still sending the current JWT via `X-API-Key`, or were still conceptually wired around `apiKey` props even though the surrounding page used cookie-backed JWT login.

## Changes Made
- **File**: `web/src/app/cortex/page.tsx`
  - Logic: Switched server-side admin data fetching from legacy API-key headers to `buildBearerHeaders(token)` and reused `getServerAuthContext()`.
- **File**: `web/src/app/users/page.tsx`
  - Logic: Switched user listing fetch to bearer auth and reused `getServerAuthContext()`.
- **File**: `web/src/app/users/[user_id]/page.tsx`
  - Logic: Switched per-user fetch to bearer auth and reused `getServerAuthContext()`.
- **Files**: `web/src/app/integrations/PluginForm.tsx`, `web/src/app/integrations/EditPluginButton.tsx`, `web/src/app/integrations/ViewSkillButton.tsx`, `web/src/app/integrations/page.tsx`
  - Logic: Renamed `apiKey` props to `token` and switched plugin catalog/schema/skill fetches to `Authorization: Bearer <token>`.

## Decisions
- Keep the cleanup scoped to admin pages already running behind JWT login, instead of attempting a broad repo-wide auth refactor.
- Standardize prop names from `apiKey` to `token` in these flows so the auth mechanism is obvious at the call site and less likely to regress.

## Verification
- [X] `rg -n 'X-API-Key' web/src -S`
- [X] `git diff --check -- web/src/app/cortex/page.tsx web/src/app/users/page.tsx web/src/app/users/[user_id]/page.tsx web/src/app/integrations/PluginForm.tsx web/src/app/integrations/EditPluginButton.tsx web/src/app/integrations/ViewSkillButton.tsx web/src/app/integrations/page.tsx web/src/components/WireLogToggle.tsx web/src/app/audit/page.tsx`
- [!] `cd web && npm run lint -- ...` still reports pre-existing lint issues in several admin files (`any`, unused imports, hook deps, unescaped apostrophes), so full lint clean status was not achievable in the current workspace without unrelated cleanup.
- Evidence:
  - `rg` found no remaining `X-API-Key` usage under `web/src`.
  - `git diff --check` passed for all edited admin files.

## Risks / Next Steps
- The affected admin files already contain pre-existing lint debt; a future cleanup pass should normalize types and hook dependencies so targeted lint can become a reliable verification step again.
