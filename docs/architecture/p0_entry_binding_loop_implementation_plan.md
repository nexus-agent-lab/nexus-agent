# P0 Entry and Binding Loop Implementation Plan

## 1. Goal

Implement the next product-critical slice for Nexus:

**low-friction family entry -> reliable binding -> permission-aware Home Assistant usage -> visible audit trail**

This plan assumes we commit to:

- Telegram as the first messaging entry
- web as fallback and handoff surface
- no new family-facing channel in this slice

That keeps the implementation aligned with current productized capabilities while improving the real user journey.

## 2. Outcome To Ship

After this slice:

1. An unbound Telegram user gets a friendlier, clearer onboarding path.
2. A user can complete binding with less operator-style friction.
3. A bound user can move from entry to a first real Home Assistant task cleanly.
4. Permission-denied and ambiguous-action flows are understandable.
5. Auth and action lifecycle events are visible to the admin.

## 3. Scope

### In Scope

- Telegram onboarding and bind UX improvements
- web fallback / Telegram handoff polish
- explicit binding-state-driven UX
- auth lifecycle audit events
- permission-denied and recovery messaging improvements
- validation of the end-to-end home control loop

### Out of Scope

- new channel integration
- full trust-tier schema implementation
- full auth-session database model
- deep permission model redesign
- general self-evolution features

## 4. Current Implementation Anchors

### Backend

- `app/core/auth_service.py`
  - bind token creation
  - Telegram login challenge lifecycle
  - identity binding and unbinding
- `app/models/user.py`
  - `User`
  - `UserIdentity`
- `app/api/auth.py`
  - bind token endpoint
  - Telegram start/status/complete handoff endpoints
- `app/models/audit.py`
  - current generic audit record

### Messaging UX

- `app/interfaces/telegram.py`
  - `/start`
  - `/bind`
  - `/unbind`
  - dynamic command refresh
  - guest vs bound welcome flow

### Web UX

- `web/src/app/login/page.tsx`
  - API key login
  - Telegram handoff flow

### Validation Docs

- `docs/auth_channel_strategy.md`
- `docs/auth_binding_state_machine.md`
- `docs/ha_p0_validation_checklist.md`
- `docs/project_focus_and_direction.md`

## 5. Delivery Strategy

Implement this in four milestones.

## 6. Milestone 1: Binding-State-Aware UX

### Objective

Make the system behave as if it has explicit binding states even before a full schema refactor.

### Product Changes

- differentiate user-facing states:
  - unbound guest
  - bind pending
  - bound/verified
  - revoked/expired flow
- improve Telegram guest onboarding copy
- improve Telegram login-handoff denial copy when account is not yet linked
- make web login page clearly position Telegram as the normal user path and API key as fallback/admin path

### Implementation Approach

Add a lightweight derived-state layer in service code rather than introducing a new table first.

Suggested additions:

- add a small helper in `AuthService` or adjacent auth module:
  - `get_binding_state(provider, provider_user_id)`
  - or `describe_identity_access(provider, provider_user_id)`
- use this helper from Telegram handlers and auth endpoints to unify wording and branching

### Files Likely To Change

- `app/core/auth_service.py`
- `app/interfaces/telegram.py`
- `app/api/auth.py`
- `web/src/app/login/page.tsx`
- optionally `app/core/i18n.py` if more strings are centralized there

### Validation

- unbound Telegram user sees clear next steps
- already-bound user gets direct welcome path
- Telegram login handoff rejects unbound user with clear recovery guidance
- login page text matches the intended product model

## 7. Milestone 2: Bind Flow Simplification

### Objective

Reduce operator friction in the Telegram + web binding path without changing the trust model yet.

### Product Changes

- make bind-token usage easier to understand
- tighten rebind/unbind feedback
- reduce places where the user has to guess the next step
- ensure the web handoff and Telegram bind flow feel like the same auth story

### Implementation Approach

Keep the existing Redis challenge/token model, but improve orchestration and UX around it.

Suggested changes:

- standardize response payloads from auth endpoints for handoff and bind errors
- unify expiration, conflict, and already-bound wording
- allow Telegram `/start` deep-link flows to branch explicitly between:
  - login handoff
  - bind handoff
  - generic onboarding
- normalize bind conflicts into a predictable service result shape

### Files Likely To Change

- `app/core/auth_service.py`
- `app/interfaces/telegram.py`
- `app/api/auth.py`
- `web/src/app/actions/auth.ts`
- `web/src/app/login/page.tsx`
- tests:
  - `tests/test_telegram_bind_flow.py`
  - `tests/test_telegram_login_handoff.py`
  - `tests/test_auth_telegram_handoff.py`

### Validation

- bind success and conflict states are understandable
- unbind leaves the user in a coherent guest flow
- Telegram handoff still completes JWT login successfully
- no regression in existing bind/login tests

## 8. Milestone 3: Permission-Denied and Recovery UX

### Objective

Improve the first-use quality of Home Assistant interactions after binding.

### Product Changes

- permission-denied replies should explain what happened and what the user can do next
- entity-not-found and ambiguous requests should bias toward clarification over confusing failure
- side-effectful actions should feel safely governed rather than randomly blocked

### Implementation Approach

Use the existing normalized runtime categories rather than inventing a second message policy.

Suggested changes:

- enrich user-facing summaries for:
  - `permission_denied`
  - `invalid_input`
  - `verification_failed`
  - `unsafe_state`
- make sure Telegram-facing output renders these as actionable guidance
- review where reviewer/skill-worker follow-up copy can expose too much internal wording

### Files Likely To Change

- `app/core/result_classifier.py`
- `app/core/worker_dispatcher.py`
- `app/core/worker_graphs/skill_worker.py`
- `app/interfaces/telegram.py`
- possibly web chat surfaces if they mirror the same summaries
- tests:
  - `tests/unit/test_worker_dispatcher.py`
  - `tests/test_agent.py`

### Validation

- non-admin restart attempt gives understandable restricted-action guidance
- missing entity path asks for clarification or reports clearly
- abnormal/unavailable state does not look like success
- wording is acceptable for a family-facing product flow

## 9. Milestone 4: Audit Coverage and Admin Visibility

### Objective

Make auth and action transitions visible enough for real operation.

### Product Changes

- operator can see:
  - bind token generated
  - bind succeeded
  - bind failed/conflicted
  - Telegram login handoff started
  - login handoff approved / expired / rejected
  - denied high-risk action attempts

### Implementation Approach

Do not redesign the full audit subsystem yet. Extend the existing generic model carefully.

Recommended first step:

- standardize `action` names for auth lifecycle events
- populate `status`, `error_message`, and `tool_args` consistently
- use correlation IDs where possible for challenge-driven flows

Suggested event names:

- `auth.bind_token_created`
- `auth.binding_succeeded`
- `auth.binding_conflict`
- `auth.binding_revoked`
- `auth.telegram_login_started`
- `auth.telegram_login_approved`
- `auth.telegram_login_rejected`
- `auth.telegram_login_completed`
- `policy.action_denied`

### Files Likely To Change

- `app/models/audit.py` if schema extension is needed
- `app/core/audit.py`
- `app/core/auth_service.py`
- `app/api/auth.py`
- `app/core/worker_dispatcher.py`
- admin/audit UI surfaces:
  - `web/src/app/audit/page.tsx`
  - `web/src/app/audit/TraceViewer.tsx`
  - or minimal dashboard equivalents already in use

### Validation

- auth lifecycle creates readable audit records
- denied actions create audit records with actor and reason
- admin can inspect at least the latest records without raw DB access

## 10. Data and Schema Decisions

### 10.1 Defer Full Binding-State Table

Do not add a dedicated auth-session or trust-tier table in this slice.

Reason:

- too much schema churn for the immediate value
- current UX issues can be improved with derived state and better audit

### 10.2 Possible Safe Additions

If needed, the safest schema additions in this slice are:

- nullable binding metadata on `UserIdentity`
  - `verified_at`
  - `revoked_at`
  - `binding_status`

But even these should be optional unless the implementation truly needs them.

### 10.3 Audit Schema

Prefer reusing `AuditLog` first.

Only extend schema if one of these becomes necessary:

- explicit event metadata beyond `tool_args`
- auth challenge correlation fields
- actor/provider distinction not representable today

## 11. Testing Plan

### Automated Tests

Expand current coverage rather than inventing entirely new test suites.

Primary targets:

- `tests/test_telegram_bind_flow.py`
- `tests/test_telegram_login_handoff.py`
- `tests/test_auth_telegram_handoff.py`
- `tests/test_auth_core.py`
- `tests/unit/test_worker_dispatcher.py`
- `tests/test_api.py`

### Manual / Checklist Validation

Add or use a concise checklist covering:

1. unbound Telegram entry
2. bind completion
3. Telegram-to-web login completion
4. first HA command after binding
5. permission-denied restricted action
6. audit visibility for the above

This should be linked with `docs/ha_p0_validation_checklist.md` rather than living only in code.

## 12. Sequencing Recommendation

Recommended order:

1. Milestone 1
2. Milestone 2
3. Milestone 4
4. Milestone 3
5. validation pass

Why audit before final UX polish on permission flows:

- once auth lifecycle changes land, we want observability before tuning the long tail of recovery messages

## 13. Rough Effort By Milestone

### Milestone 1

- 1 to 2 days

### Milestone 2

- 2 to 3 days

### Milestone 3

- 1.5 to 2.5 days

### Milestone 4

- 1.5 to 3 days

### Validation and cleanup

- 1 to 2 days

Total expected effort:

- **7 to 12.5 working days**

This is consistent with the earlier estimate and makes room for test and UX iteration.

## 14. Main Risks

### Risk 1: UX copy gets fixed in too many places

Mitigation:

- centralize wording where possible
- define a small set of auth outcome codes and map them to copy

### Risk 2: Auth flow logic drifts between web and Telegram

Mitigation:

- move outcome shaping into `AuthService` or a shared auth response layer

### Risk 3: Audit becomes noisy but not useful

Mitigation:

- define a narrow event list first
- optimize for “what happened, for whom, and why denied”

### Risk 4: HA flow issues are mistaken for auth issues

Mitigation:

- validate entry/bind/login separately from HA action success
- use explicit checklist steps

## 15. Definition of Done

This implementation plan is complete when:

- Telegram and web tell one coherent auth story
- binding and handoff states are clear to normal users
- the first family-use HA loop works with understandable failure handling
- auth and denied-action events are visible in audit
- tests and checklist validation cover the full path

## 16. Recommended Next Engineering Task

If implementation starts immediately, the first concrete task should be:

**Milestone 1: binding-state-aware UX and shared auth outcome shaping**

Reason:

- it unblocks all later work
- it reduces copy drift
- it keeps the slice grounded in product experience instead of premature schema work
