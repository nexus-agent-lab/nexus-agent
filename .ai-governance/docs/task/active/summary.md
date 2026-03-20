# Summary

## Branch Intent
Advance P0-2 auth/login/permission UX by moving from Telegram-only practical binding toward a unified Telegram↔web handoff flow, while preserving the HA P0-1 validation baseline for later manual testing.

## Current State
- Added `docs/ha_p0_validation_checklist.md` and linked it from `docs/task.md` so HA reliability issues can be tracked and marked fixed over time.
- Added auth design docs: `docs/auth_channel_strategy.md` and `docs/auth_binding_state_machine.md`.
- Committed earlier work as `59ed1f1` (`tighten bind UX and add HA validation checklist`).
- Implemented first Telegram↔web handoff MVP:
  - Redis-backed challenge/exchange helpers in `app/core/auth_service.py`
  - `POST /api/auth/telegram/start`, `GET /api/auth/telegram/status`, `POST /api/auth/telegram/complete` in `app/api/auth.py`
  - Telegram `/start login_<challenge>` approval path in `app/interfaces/telegram.py`
  - Web login page now offers `Continue with Telegram` and completes via `web/src/app/api/auth/telegram/complete/route.ts`
  - Unbound Telegram users now mark the challenge as `rejected_unbound` so web stops polling instead of hanging
- Focused tests added and passing:
  - `tests/test_auth_telegram_handoff.py`
  - `tests/test_telegram_login_handoff.py`
  - Verified with `uv run pytest tests/test_auth_telegram_handoff.py tests/test_telegram_login_handoff.py -v` => 6 passed
- Oracle-style review concluded the MVP handoff pattern is acceptable for P0, and the unbound-user polling issue was the only must-fix in this slice; that fix is already applied.

## Known Risks
- Major pre-existing auth weakness remains: the Next.js web layer decodes JWT without signature verification and extracts `api_key` from the payload for backend requests. Oracle flagged this as the next must-fix security issue.
- Python LSP reports many type errors in `app/interfaces/telegram.py` and `app/core/auth_service.py`, but these are largely existing repo typing noise / nullable PTB issues rather than verified runtime failures from this slice. No type-suppression was added.
- Full end-to-end browser verification of the Telegram↔web handoff was not run; validation is currently backend/unit-focused only.
- New handoff code is not yet committed.

## Next Action
Harden web/backend auth by moving web requests off decoded JWT `api_key` extraction and onto backend-verified Bearer JWT handling, then update the web app to use that path consistently.
