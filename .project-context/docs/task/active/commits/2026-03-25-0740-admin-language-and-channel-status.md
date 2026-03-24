# Commit: 2026-03-25-0740-admin-language-and-channel-status

## Intent
Repair the admin users page channel-status visibility after the previous regression, and add a first-pass web UI language switching page for Chinese and English.

## Previous Context
- The first attempt to expose Telegram/WeChat state in the users list overloaded `GET /users/` and caused the user-management page to fall back to an empty table when that response path broke.
- The admin web surface had no real frontend locale layer; only backend/chat strings in `app/core/i18n.py` existed.

## Changes Made
- **File**: `app/api/users.py`
  - Restored `GET /users/` to the original stable response shape.
  - Added `GET /users/channel-statuses` for admin-only aggregated Telegram/WeChat state.
- **File**: `web/src/app/users/page.tsx`
  - Switched the users list to load the base user list and the aggregated channel-status map separately.
  - Rendered Telegram/WeChat bound state from the dedicated admin summary endpoint.
  - Localized the page strings through the new locale dictionary.
- **Files**: `web/src/lib/locale.ts`, `web/src/app/actions/preferences.ts`
  - Added a minimal frontend locale layer backed by a `nexus_locale` cookie.
- **Files**: `web/src/app/language/page.tsx`, `web/src/app/language/LanguageSettingsForm.tsx`
  - Added a dedicated language settings page with Chinese/English switching.
- **Files**: `web/src/app/layout.tsx`, `web/src/components/Layout.tsx`
  - Wired locale resolution into the root layout.
  - Added a sidebar entry for the new language page.
  - Localized primary navigation labels and a few shared shell strings.

## Decisions
- Chose a dedicated `channel-statuses` endpoint instead of overloading `GET /users/` again, because channel aggregation is an admin presentation concern and should not be able to blank out the core user list.
- Chose a cookie-backed locale setting as the first web UI localization slice because it works immediately without a route-prefix migration or a large app-wide i18n framework conversion.
- Scoped the first locale pass to visible shell/navigation and the users page so the feature becomes usable quickly without blocking on a full-app translation sweep.

## Verification
- `uv run ruff check app/api/users.py`
- `cd web && npm run lint -- 'src/app/layout.tsx' 'src/components/Layout.tsx' 'src/lib/locale.ts' 'src/app/language/page.tsx' 'src/app/language/LanguageSettingsForm.tsx' 'src/app/actions/preferences.ts' 'src/app/users/page.tsx'`
- Evidence:
  - Ruff passed for the updated users API.
  - ESLint passed for the updated locale/users files with one pre-existing `Layout.tsx` `<img>` optimization warning and no new errors.
