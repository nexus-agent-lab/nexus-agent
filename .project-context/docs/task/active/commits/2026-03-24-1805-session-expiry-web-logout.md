# Commit: 2026-03-24-1805-session-expiry-web-logout

## Intent
Fix the admin web UX where a backend `401 Unauthorized` toast appeared, but the browser session stayed on the current page instead of clearing the expired login state and returning to `/login`.

## Previous Context
The admin web surface had already migrated from `X-API-Key` to bearer JWT auth. Middleware and server-rendered page guards would reject missing or expired cookies, but several client-side fetch paths only showed a toast on `401` and did not clear the `httpOnly` cookie.

## Changes Made
- **Files**: `web/src/app/actions/auth.ts`, `web/src/lib/client-auth.ts`
  - Logic: Split cookie clearing from redirecting by adding `clearSession()`, then kept the actual client-side recovery in one shared `handleUnauthorizedSession(...)` helper.
- **Files**: `web/src/components/AuthRedirectOnUnauthorized.tsx`, `web/src/app/layout.tsx`
  - Logic: Added a root-layout fetch interceptor that watches browser-side Bearer-authenticated requests and globally handles `401` by clearing session state and navigating back to `/login`.
- **File**: `web/src/app/actions/plugins.ts`
  - Logic: Standardized plugin-related server actions so missing-token and backend `401` cases clear the stale cookie and redirect server-side to `/login` instead of bubbling a custom `authExpired` branch back to each component.
- **Files**: `web/src/app/integrations/PluginForm.tsx`, `web/src/app/integrations/EditPluginButton.tsx`, `web/src/app/integrations/ViewSkillButton.tsx`, `web/src/app/integrations/ReloadMCPButton.tsx`, `web/src/components/WireLogToggle.tsx`
  - Logic: Removed the per-component unauthorized branching that had started to spread after the first patch; these components now rely on the global browser interceptor or server-action redirect path.

## Decisions
- Prefer one root-level browser fetch interceptor over scattered `response.status === 401` checks in admin components.
- Keep server-action unauthorized handling server-side by redirecting from the action itself, instead of inventing per-action `authExpired` result branches.
- Clear the `httpOnly` cookie on the server side before redirecting so the browser does not immediately land back in another stale-auth edge case.
- Standardize the user-facing copy to a recovery-oriented message: `Session expired. Please log in again.`

## Verification
- [X] `cd web && npm run lint -- src/lib/client-auth.ts src/app/actions/auth.ts src/app/actions/plugins.ts src/app/integrations/PluginForm.tsx src/components/WireLogToggle.tsx src/app/integrations/EditPluginButton.tsx src/app/integrations/ViewSkillButton.tsx src/app/integrations/ReloadMCPButton.tsx`
- [X] `git diff --check -- web/src/app/actions/auth.ts web/src/lib/client-auth.ts web/src/app/actions/plugins.ts web/src/app/integrations/PluginForm.tsx web/src/components/WireLogToggle.tsx web/src/app/integrations/EditPluginButton.tsx web/src/app/integrations/ViewSkillButton.tsx web/src/app/integrations/ReloadMCPButton.tsx`
- Evidence:
  - targeted frontend lint passed for all changed auth-recovery files
  - diff hygiene check passed with no whitespace or merge-marker issues

## Risks / Next Steps
- Manual browser validation is still needed for the exact revoked-token path that originally showed the toast in `PluginForm`.
- Other admin surfaces still using server actions outside the integrations area may benefit from the same `authExpired` pattern if revoked tokens surface there too.
