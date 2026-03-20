# Auth Binding State Machine

> Status: execution spec proposal
>
> Depends on: `docs/auth_channel_strategy.md`

---

## 1. Purpose

This document turns the channel auth strategy into an execution-oriented specification.

It defines:

- canonical terms
- binding states
- trust tiers
- state transitions
- audit events
- channel-specific onboarding rules

The goal is to let Nexus evolve from a Telegram-centric bind flow into a unified, multi-channel, governable access system without breaking the existing architecture.

---

## 2. Design constraints from the current repository

The current codebase already has:

- `User`
- `UserIdentity`
- `role` (`admin`, `user`, `guest`)
- `policy`
- bind token generation and verification
- provider-based identity resolution
- a basic `AuditLog`

Current limitations:

- no explicit binding status field
- no explicit trust tier field
- no dedicated auth session model for channel handoff
- audit model is generic and not yet specialized for auth lifecycle events

So this spec is intentionally written in two layers:

1. **logical model** — what the system should mean
2. **implementation mapping** — how to evolve from current tables and services

---

## 3. Canonical concepts

### 3.1 Principal

The canonical Nexus identity.

This is currently the `User` record.

A principal owns:

- role
- policy
- household or enterprise membership
- long-term permissions
- audit ownership

### 3.2 Channel identity

An external identity observed from a channel or login surface.

Examples:

- Telegram `user.id`
- WeCom `corp_id + userid`
- Feishu `open_id`
- WeChat Official Account `openid`
- WeChat `unionid` if available

### 3.3 Binding

A verified relationship between a channel identity and a principal.

Current implementation equivalent:

- `UserIdentity`

Future implementation should distinguish:

- whether the binding is active
- what trust tier it has
- how it was verified

### 3.4 Auth session / access grant

A temporary server-side record that says:

- this channel identity has been verified
- it was mapped to this principal
- it currently has this trust level
- it was established by this auth method

This does **not** have to be implemented first as a database table, but the system should behave as if this concept exists.

---

## 4. Trust tiers

### Tier A — org-verified

Meaning:

- identity comes from an organization-managed source
- channel or login provider is suitable as a strong source of membership

Examples:

- WeCom internal employee identity
- future SSO / enterprise IdP

Default implications:

- can create an authenticated session directly
- can map to enterprise user role quickly
- still may require action-level confirmation for dangerous operations

### Tier B — channel-verified

Meaning:

- platform strongly identifies the same user over time
- but does not prove organization membership by itself

Examples:

- Telegram user ID
- Feishu external identity

Default implications:

- valid for bound personal access
- valid for family/home scenarios after linking
- not sufficient by itself for enterprise admin-grade trust

### Tier C — bootstrap / guest

Meaning:

- channel can reach a user and identify a stable account at some level
- but it is not enough for privileged access by default

Examples:

- WeChat Official Account `openid`
- unauthenticated web flow before linking
- first-touch channel identity before approval/linking

Default implications:

- can onboard
- can request linking
- can receive instructions, invites, or approval prompts
- should not perform sensitive control-plane or device actions by default

---

## 5. Binding states

These are the recommended logical states for each channel binding.

### 5.1 `pending`

Meaning:

- the external identity has been observed
- linking has started, but not completed

Examples:

- user opened a deep link but has not confirmed
- user entered from Official Account but has not accepted invite/bind flow yet
- admin initiated a bind flow for a user but user has not completed it

Allowed capabilities:

- help
- onboarding
- linking prompts
- identity confirmation

### 5.2 `verified`

Meaning:

- the external identity is actively linked to a principal
- the link is valid and usable

Allowed capabilities:

- normal authenticated access, subject to role/policy/trust tier

### 5.3 `guest_only`

Meaning:

- the system recognizes the channel identity only as a low-trust bootstrap identity
- there is no full principal link yet, or the channel is intentionally limited

Typical examples:

- WeChat Official Account first-touch user
- low-trust public messaging entry

Allowed capabilities:

- view guidance
- request access
- receive invite approval result
- perform explicitly safe guest features only

### 5.4 `revoked`

Meaning:

- this binding previously existed, but is no longer valid

Causes:

- admin unbound it
- user unbound it
- security review revoked it
- tenant membership changed

Allowed capabilities:

- no authenticated access based on that old binding
- may re-enter onboarding/linking flow

### 5.5 `blocked`

Meaning:

- the system intentionally prevents this channel identity from becoming active

Examples:

- security issue
- abuse/spam source
- provider identity explicitly denied

Allowed capabilities:

- usually no access beyond a generic denial or escalation path

---

## 6. Principal access states

Separately from binding state, the principal itself has an effective access posture.

### `guest`

Current implementation already supports this via `User.role == "guest"`.

Use when:

- principal exists but is not fully linked/approved
- user is in bootstrap mode

### `user`

Normal authenticated user.

### `admin`

Full administrative access.

Important:

- channel trust tier should still affect how freely a session can perform risky actions
- do not assume every authenticated channel is equally safe just because the principal has a high role

---

## 7. State transition model

### 7.1 Channel entry -> binding transition

#### Path A: already verified binding

1. channel identity enters
2. matching binding exists in `verified`
3. principal resolved
4. session/access granted according to trust tier + principal role

#### Path B: pending bind flow

1. channel identity enters
2. no verified binding exists
3. system creates or interprets this as `pending`
4. user completes bind/invite/approval flow
5. binding becomes `verified`

#### Path C: bootstrap guest flow

1. channel identity enters from low-trust channel
2. no verified binding exists
3. system treats identity as `guest_only`
4. user can only proceed through explicit linking or approval

#### Path D: revoked or blocked

1. channel identity enters
2. system finds revoked/blocked state
3. access is denied or rerouted to recovery/onboarding

---

## 8. Recommended transition table

| Event | Current State | Next State | Notes |
|---|---|---|---|
| User starts bind flow | none | `pending` | e.g. Telegram deep link / web handoff / invite acceptance |
| Bind token validated | `pending` | `verified` | current Telegram model maps here |
| Admin creates guest bootstrap access | none | `guest_only` | useful for OA/bootstrap channels |
| Approval granted for guest bootstrap | `guest_only` | `verified` | after invite/admin approval/link |
| User unbinds channel | `verified` | `revoked` | current `unbind_identity` maps here conceptually |
| Admin revokes channel | `verified` | `revoked` | audit required |
| Security denylist applied | any | `blocked` | strong denial path |
| Re-link after revocation | `revoked` | `pending` | re-onboarding |

---

## 9. Channel-specific execution rules

### 9.1 Telegram

#### Current fit

Telegram is already the best implemented bind channel.

#### Recommended state machine usage

- first message without binding -> `pending` style onboarding or guest prompt
- bind token / deep link success -> `verified`
- explicit `/unbind` -> `revoked`

#### Recommended next evolution

- support deep-link bind (`/start <token>`) consistently
- add web <-> Telegram handoff using short-lived server-side auth challenge

### 9.2 Web

#### Current fit

Web login currently behaves like a technical/admin path.

#### Recommended state machine usage

- unauthenticated web user -> `pending` access flow, not immediate full login by default
- handoff via Telegram or WeCom can promote web session into authenticated state

#### Recommended next evolution

- add device-code or channel-confirm flow
- support “continue with Telegram” / “continue with WeCom” style verified handoff

### 9.3 WeCom

#### Recommended usage

- WeCom OAuth identifies enterprise user
- if mapping exists -> `verified`
- if not -> `pending` first-bind flow
- depending on org policy, first-bind may auto-link or require admin approval

#### Why it matters

- this is the cleanest enterprise entry path
- strongest fit for role, membership, and audit

### 9.4 WeChat Official Account

#### Recommended usage

- initial identity is usually `guest_only`
- never assume follow/openid alone implies full trust
- use OA as discovery + bootstrap + invite acceptance channel

#### Promotion path

- OA guest -> invite/bind/approval -> `verified`

---

## 10. Session rules

Even before a dedicated session table exists, the system should behave with these rules:

### Rule 1

Every authenticated request/message should resolve to:

- principal
- binding state
- trust tier
- auth method

### Rule 2

High-risk actions should consider both:

- principal role/policy
- session trust tier

Example:

- an `admin` using a lower-trust bootstrap channel should potentially face additional confirmation for sensitive actions

### Rule 3

Guest/bootstrap channels should never silently inherit privileged capability just because the underlying person may already be known elsewhere.

There must be an explicit server-side link resolution and policy check.

---

## 11. Audit event model

Current `AuditLog` is generic. Auth should standardize a small set of event names.

### 11.1 Required auth event types

- `auth_entry_detected`
- `auth_bind_started`
- `auth_bind_succeeded`
- `auth_bind_failed`
- `auth_bind_revoked`
- `auth_guest_session_started`
- `auth_session_granted`
- `auth_session_denied`
- `auth_step_up_required`
- `auth_identity_conflict`

### 11.2 Minimum event fields

Each auth audit event should capture:

- `trace_id`
- `user_id` if known
- `channel`
- `provider_user_id` or masked external identifier
- `binding_state_before`
- `binding_state_after`
- `trust_tier`
- `auth_method`
- `status`
- `error_message` if any
- `meta` for risk/action context

### 11.3 Example mappings

#### Telegram bind success

- event: `auth_bind_succeeded`
- channel: `telegram`
- auth_method: `bind_token`
- state: `pending -> verified`

#### Official Account first-touch user

- event: `auth_guest_session_started`
- channel: `wechat_oa`
- auth_method: `oauth_h5_openid`
- state: `none -> guest_only`

#### WeCom login success

- event: `auth_session_granted`
- channel: `wecom`
- auth_method: `oauth_code`
- trust tier: `Tier A`

---

## 12. Implementation mapping from current code

This section keeps the spec grounded in today’s codebase.

### Already available

- `User` can remain the principal model initially
- `UserIdentity` can remain the binding ledger initially
- `AuthService.create_bind_token()` and `verify_bind_token()` already support bind-token flows
- `AuthService.bind_identity()` already supports one-to-one provider linking

### Recommended near-term additions

The following should be added incrementally when implementation begins:

#### A. Binding metadata

Extend `UserIdentity` or equivalent with fields such as:

- `binding_status`
- `trust_tier`
- `verified_at`
- `auth_method`
- `revoked_at`
- `revoked_reason`

#### B. Optional auth session table

Future optional model:

- `AuthSession` or equivalent server-side access grant record

#### C. Auth audit specialization

Either:

- extend `AuditLog.action` conventions only

or

- add structured auth audit helpers/services

---

## 13. Recommended near-term implementation order

### Step 1

Make Telegram + web share one logical linking model.

This is the highest-value next implementation step.

### Step 2

Introduce binding metadata fields and auth audit event conventions.

### Step 3

Implement web handoff / device-code style auth.

### Step 4

Implement WeCom as the first new strong identity channel.

### Step 5

Implement WeChat Official Account as guest/bootstrap entry.

---

## 14. Decision rules for future implementations

Whenever a new channel is added, answer these questions first:

1. What external identifier does the platform provide?
2. Is that identifier org-verified, channel-verified, or bootstrap-only?
3. Should first contact enter `pending`, `verified`, or `guest_only`?
4. What is the allowed capability before explicit linking?
5. What audit events must be recorded?

If these questions are not answered, the channel should not be added yet.

---

## 15. Near-term acceptance criteria

This state machine is ready to drive implementation when the team agrees on all of the following:

- one principal can own many channel bindings
- binding state is separate from principal role
- trust tier is separate from role
- Telegram and web should converge on one auth/linking model
- WeCom should be the first strong enterprise auth channel
- WeChat Official Account should start as guest/bootstrap, not full-trust by default
