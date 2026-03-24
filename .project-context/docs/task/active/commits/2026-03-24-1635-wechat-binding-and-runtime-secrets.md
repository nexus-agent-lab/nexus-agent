# Commit: 2026-03-24-1635-wechat-binding-and-runtime-secrets

## Intent
Finish productizing the WeChat user-binding flow in the admin UI and remove the unsafe runtime-secret defaults that were causing JWT and encryption warnings.

## Previous Context
WeChat had been reworked into a user-level QR binding model, but the admin entry points and success-state rendering were still rough. At the same time, runtime logs still warned that `NEXUS_MASTER_KEY` was missing and the JWT signing key was shorter than the recommended SHA-256 HMAC minimum.

## Changes Made
- **Files**: `web/src/app/users/page.tsx`, `web/src/app/users/[user_id]/page.tsx`, `web/src/app/users/[user_id]/WeChatBindingCard.tsx`, `web/src/app/users/CreateUserForm.tsx`
  - Logic: Restored the add-user entry on the users page, clarified the `Manage & Bind` path, improved the WeChat bind modal to handle link-style QR payloads, and rendered a proper success state after the session becomes `bound`.
- **Files**: `app/api/users.py`, `app/interfaces/wechat.py`, `app/core/worker.py`, `tests/test_wechat_interface.py`
  - Logic: Completed the admin-driven WeChat binding flow, kept Telegram-only chat-side bind interception, and supported per-user WeChat runtime sessions.
- **Files**: `app/core/security.py`, `app/core/auth.py`, `app/api/auth.py`, `app/main.py`, `tests/test_auth_core.py`, `tests/unit/test_security.py`
  - Logic: Added startup-time secure secret provisioning and dynamic JWT secret resolution so missing/short secrets no longer cause runtime security warnings.
- **File**: `.env.example`
  - Logic: Updated security and WeChat env docs to reflect the new auto-generated defaults and removed obsolete global WeChat token settings.

## Decisions
- Treat `liteapp.weixin.qq.com/...` payloads as login links rather than direct image resources.
- Keep user-facing QR preview and direct-link affordances in the modal, but rely on the underlying user-level WeChat session model instead of global bot login.
- Prefer auto-generated persisted runtime secrets over insecure static defaults or plaintext bypass on first run.

## Verification
- [X] `uv run pytest tests/test_auth_core.py tests/unit/test_security.py tests/test_wechat_interface.py tests/test_auth_telegram_handoff.py`
- [X] `uv run ruff check app/core/security.py app/core/auth.py app/api/auth.py app/main.py tests/test_auth_core.py tests/unit/test_security.py`
- [X] `cd web && npm run lint -- 'src/app/users/page.tsx' 'src/app/users/CreateUserForm.tsx' 'src/app/users/[user_id]/page.tsx' 'src/app/users/[user_id]/WeChatBindingCard.tsx'`
- Evidence:
  - Python regression/security suite passed (`22 passed`)
  - targeted frontend lint passed for the updated users/WeChat files

## Risks / Next Steps
- Restart the backend to let the generated `JWT_SECRET` and `NEXUS_MASTER_KEY` take effect in the running process and confirm the previous warnings disappear.
- Real-device confirmation is still needed for the first inbound WeChat message after binding, to ensure the correct user receives the session.
