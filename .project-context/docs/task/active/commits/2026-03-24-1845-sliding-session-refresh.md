# Commit: 2026-03-24-1845-sliding-session-refresh

## Intent
Replace the fixed 24-hour admin web session with a sliding session so normal active use does not unexpectedly expire after one day.

## Previous Context
JWT and cookie lifetime were both fixed at 24 hours. The earlier session-expiry recovery work ensured the UI logged out cleanly on `401`, but active users would still hit expiry once the original token aged out.

## Changes Made
- **File**: `app/api/auth.py`
  - Logic: Introduced `ACCESS_TOKEN_EXPIRE_SECONDS`, added `POST /auth/refresh`, and included `expires_in` in issued token responses so the web layer can stay aligned with backend TTL.
- **Files**: `web/src/app/actions/auth.ts`, `web/src/app/auth/telegram/complete-web/route.ts`
  - Logic: Centralized access-token cookie writing, added `refreshSession()`, and switched cookie max-age to use backend-provided TTL metadata.
- **Files**: `web/src/components/SessionKeepAlive.tsx`, `web/src/app/layout.tsx`
  - Logic: Added a root-mounted session keepalive component that refreshes the session about one hour before expiry and reschedules safely across retries/background-tab states.
- **File**: `tests/test_auth_refresh.py`
  - Logic: Added API coverage for the new refresh endpoint and its auth requirement.

## Decisions
- Keep the base TTL at 24 hours, but make it sliding by reissuing the token before expiry while the app is actively open.
- Refresh through the backend rather than locally extending the cookie, because the JWT `exp` claim remains the real source of truth.
- Use backend-provided `expires_in` metadata to avoid future drift between backend token lifetime and frontend cookie lifetime.

## Verification
- [X] `uv run pytest tests/test_auth_refresh.py tests/test_auth_core.py`
- [X] `cd web && npm run lint -- src/components/SessionKeepAlive.tsx src/components/AuthRedirectOnUnauthorized.tsx src/lib/client-auth.ts src/app/layout.tsx src/app/actions/auth.ts src/app/auth/telegram/complete-web/route.ts`
- [X] `git diff --check -- app/api/auth.py web/src/app/actions/auth.ts web/src/app/layout.tsx web/src/components/SessionKeepAlive.tsx web/src/app/auth/telegram/complete-web/route.ts tests/test_auth_refresh.py`

## Risks / Next Steps
- Manual browser validation is still needed to confirm long-lived tabs refresh as expected across visibility changes.
- The backend currently uses `datetime.utcnow()`, which emitted a deprecation warning under Python 3.14 during tests and should be modernized separately.
