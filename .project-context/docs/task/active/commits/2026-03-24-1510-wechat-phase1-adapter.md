# Commit: 2026-03-24-1510-wechat-phase1-adapter

## Intent
Start the WeChat channel integration with a minimal but real transport path so Nexus can validate whether WeChat is a practical family-facing primary entry.

## Previous Context
Telegram/admin/P0 auth and recovery fixes had stabilized, and the next strategically important channel spike was WeChat. The codebase already had `ChannelType.WECHAT` plus the generic MQ/dispatcher/identity architecture, but no actual WeChat adapter.

## Changes Made
- **File**: `app/interfaces/wechat.py`
  - Logic: Added QR login bootstrap, bot-token management, `getupdates` polling, inbound text normalization, outbound `sendmessage`, typing support, and WeChat audit events.
- **Files**: `app/main.py`, `app/core/dispatcher.py`
  - Logic: Wired WeChat startup and outbound dispatch into the existing runtime.
- **Files**: `app/core/worker.py`, `app/core/auth_service.py`
  - Logic: Improved channel-generic bind handling so plain `bind 123456` works well for WeChat-style chat UX; corrected bind-token audit metadata so it is no longer Telegram-specific.
- **Files**: `.env.example`, `tests/test_wechat_interface.py`, `tests/test_worker_channel_helpers.py`
  - Logic: Documented WeChat env vars and added focused tests for protocol helpers and channel-binding helpers.

## Decisions
- Keep this phase intentionally narrow: text in, text out, typing, and login transport only.
- Reuse the existing generic binding model (`provider="wechat"`, `provider_user_id=from_user_id`) rather than inventing a WeChat-specific identity subsystem.
- Make bind command parsing more channel-natural now, instead of forcing slash commands onto channels where that interaction is awkward.

## Verification
- [X] `uv run pytest tests/test_wechat_interface.py tests/test_worker_channel_helpers.py tests/test_auth_telegram_handoff.py tests/test_telegram_bind_flow.py`
- [X] pre-commit staged checks during `git commit`
- Evidence:
  - targeted transport/bind regression suite passed (`18 passed`)
  - staged pre-commit related suite passed (`62 passed`)

## Risks / Next Steps
- The current implementation is based on local protocol docs and assumptions; it still needs a real-device pass against live iLink payloads.
- Most valuable next validation:
  - QR login completion
  - real inbound payload shape
  - outbound reply success with cached `context_token`
  - WeChat-side `bind 123456` behavior
