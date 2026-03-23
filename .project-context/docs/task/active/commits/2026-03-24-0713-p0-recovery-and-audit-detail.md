# Commit: 2026-03-24-0713-p0-recovery-and-audit-detail

## Intent
Improve the P0 permission-denied / recovery / audit slice so family-facing failures are more actionable and admins can see key auth and denied-action lifecycle events.

## Previous Context
Admin bearer-auth fixes were already in place and the next planned product slice was Milestone 3/4 from the entry-binding implementation plan: clearer denied/recovery UX plus better audit visibility. Existing result summaries were still terse, and auth lifecycle events were not consistently recorded in audit logs.

## Changes Made
- **File**: `app/core/result_classifier.py`
  - Logic: Reworded `permission_denied`, `invalid_input`, and `unsafe_state` summaries to be more recovery-oriented and user-facing.
- **File**: `app/core/worker_dispatcher.py`
  - Logic: Added classification-aware recovery guidance so report messages suggest the right next step based on category instead of always using the same generic fallback.
- **Files**: `app/core/audit.py`, `app/core/auth_service.py`, `app/api/auth.py`, `app/interfaces/telegram.py`
  - Logic: Added completed audit-event helpers and now record structured auth/policy lifecycle events for bind token creation, bind success/conflict/failure/revocation, Telegram login start/approve/reject/complete, and policy action denial.
- **Files**: `tests/test_auth_telegram_handoff.py`, `tests/test_telegram_bind_flow.py`, `tests/unit/test_worker_dispatcher.py`
  - Logic: Added coverage for failed handoff audit logging, bind failure/conflict audit logging, and permission-denied recovery wording.

## Decisions
- Keep the audit enhancement incremental by reusing the existing generic audit model with clearer `action` names, instead of redesigning the subsystem first.
- Improve denied/recovery wording at the classifier/dispatcher layer so Telegram/web/report flows can benefit immediately without a larger channel-by-channel copy rewrite.

## Verification
- [X] `uv run pytest tests/test_auth_telegram_handoff.py tests/test_telegram_bind_flow.py tests/unit/test_worker_dispatcher.py tests/unit/test_audit.py`
- Evidence:
  - `59 passed`

## Risks / Next Steps
- Audit data is now richer, but the admin audit UI still treats events generically; a follow-up could add filters or badges for auth/policy event families.
- Permission-denied copy is better, but real-device testing should confirm whether entity-not-found and unsafe-state wording feels natural enough in family use.
