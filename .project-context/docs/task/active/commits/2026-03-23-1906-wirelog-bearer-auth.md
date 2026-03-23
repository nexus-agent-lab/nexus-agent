# Commit: 2026-03-23-1906-wirelog-bearer-auth

## Intent
Fix the admin audit page so toggling wire logging works for signed-in admins instead of failing with `Invalid API Key`.

## Previous Context
The audit page already loaded traces and logs using the signed-in JWT. However, the `WireLogToggle` client component still sent that JWT in the legacy `X-API-Key` header when calling `/admin/config`, which caused backend auth to treat it as an API key lookup and reject it.

## Changes Made
- **File**: `web/src/components/WireLogToggle.tsx`
  - Logic: Renamed the prop from `apiKey` to `token`, switched both config fetch/update requests to `Authorization: Bearer <token>`, and updated the unauthorized toast copy to reflect session-based auth.
- **File**: `web/src/app/audit/page.tsx`
  - Logic: Passed the JWT to `WireLogToggle` using the new `token` prop name for clarity and consistency with the rest of the audit page.

## Decisions
- Keep the fix narrow and aligned with the existing auth migration rather than reintroducing legacy API-key handling into this admin path.
- Make the prop name explicit so future edits do not accidentally treat bearer tokens as API keys again.

## Verification
- [X] `cd web && npm run lint -- src/components/WireLogToggle.tsx src/app/audit/page.tsx`
- Evidence:
  - ESLint completed successfully for both edited files.

## Risks / Next Steps
- Other admin/client components may still have similar legacy `X-API-Key` usage and should be audited if they are now reached from JWT-backed pages.
