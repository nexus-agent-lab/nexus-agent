# Commit: 2026-03-25-0649-user-channel-binding-visibility

## Intent
Polish the admin user-management surface so channel binding state is visible at a glance and the WeChat detail view no longer suggests a fresh bind when the user is already connected.

## Previous Context
- The admin user list required drilling into each user detail page to understand channel state.
- The WeChat binding card always rendered a `Bind WeChat` button before and after connection, which was confusing once a user already had an active WeChat session.
- Telegram binding state existed in `UserIdentity`, while WeChat binding state existed in per-user secrets/runtime status, but the admin UI did not aggregate those two sources into a single status view.

## Changes Made
- **File**: `app/api/users.py`
  - Added `UserSummaryResponse` so `GET /users/` returns `telegram_bound`, `telegram_username`, `wechat_bound`, and `wechat_polling_active`.
  - Aggregated Telegram state from `UserIdentity` rows and WeChat state from user-scoped `WECHAT_BOT_TOKEN` secrets plus runtime polling status.
- **File**: `web/src/app/users/page.tsx`
  - Added direct Telegram and WeChat status columns to the admin user list.
  - Simplified the action label from `Manage & Bind` to `Manage` because binding is no longer the only relevant activity.
  - Updated supporting copy to reflect list-level channel visibility.
- **File**: `web/src/app/users/[user_id]/page.tsx`
  - Added server-side fetches for `GET /users/{id}/bindings` and `GET /users/{id}/wechat/status`.
  - Rendered an identity summary card that shows bound/not-bound state for both Telegram and WeChat.
- **File**: `web/src/app/users/[user_id]/WeChatBindingCard.tsx`
  - Removed the default top-right bind button once WeChat is already connected.
  - Added a connected badge plus an explicit `Reconnect` action inside the connected state instead of pretending the user is unbound.

## Decisions
- Chose to hide the default bind CTA for already-connected WeChat users instead of adding unbind in the same pass, because unbind would require new backend/runtime teardown behavior that does not exist yet.
- Kept reconnect available so admins can intentionally rotate or re-establish a WeChat session without overloading the primary connected-state UI.
- Aggregated status in the backend list endpoint so the users table can render channel state without extra per-row client fetches.

## Verification
- `uv run ruff check app/api/users.py`
- `cd web && npm run lint -- 'src/app/users/page.tsx' 'src/app/users/[user_id]/page.tsx' 'src/app/users/[user_id]/WeChatBindingCard.tsx'`
- Evidence:
  - Ruff passed for the updated users API.
  - Targeted frontend ESLint passed for the updated users pages and WeChat binding card.
