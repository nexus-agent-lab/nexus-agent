# Authentication & Channel Access Strategy

> Status: proposed near-term design
>
> Goal: reduce onboarding friction beyond Telegram-only binding while preserving governance, auditability, and role-based control.

---

## 1. Why this document exists

The current repository already has a **generic identity model** and **channel-aware message routing**, but the practical user onboarding flow is still concentrated in Telegram.

Current product direction says Nexus should be:

- mobile-first
- messaging-first
- multi-user
- governable
- low-friction for normal users

That means authentication should not be designed as a web-admin-only workflow or a developer-style API key flow.

Instead, Nexus needs a unified model where:

1. users can enter from multiple messaging/web channels with low friction
2. channel identity is linked to a single Nexus principal
3. permissions and audit stay attached to the Nexus principal, not raw chat IDs
4. different channels can have different trust levels

---

## 2. Current state in the repository

### 2.1 What already exists

The backend already has the right basic foundation:

- `UserIdentity(provider, provider_user_id, provider_username)` as the generic binding model
- `AuthService` for bind token creation, verification, and identity binding
- worker-side identity resolution by `provider + provider_user_id`
- role-based permission model (`admin`, `user`, `guest`)
- audit-oriented product direction

Relevant files:

- `app/core/auth_service.py`
- `app/models/user.py`
- `app/core/worker.py`
- `app/core/mq.py`
- `docs/architecture/identity_system.md`

### 2.2 What is actually productized today

In practice, only **Telegram** has a complete user-facing binding experience:

- guest onboarding message
- `/bind`
- interactive bind flow
- `/unbind`
- menu refresh after binding

Relevant files:

- `app/interfaces/telegram.py`
- `web/src/app/users/[user_id]/page.tsx`
- `tests/test_telegram_bind_flow.py`

### 2.3 Current limitations

#### A. Telegram-only in practice

The system is not Telegram-only at the data-model layer, but it is Telegram-only at the product UX layer.

#### B. Web and chat are split into different auth stories

Current web login is effectively an admin/developer-style flow:

- username + API key -> JWT

This is not a low-friction end-user entry model and does not unify with chat binding.

#### C. Bind flow is too admin-mediated

Current flow is mostly:

1. admin creates or manages user in dashboard
2. admin generates bind token
3. user manually enters token in Telegram

This is workable for technical users, but too heavy for family members and many normal users.

#### D. Other channels are partial or planned

- **Feishu**: transport exists, but onboarding/bind UX is not productized like Telegram
- **WeCom**: not implemented yet as a real auth entry point
- **WeChat Official Account**: not implemented yet as a real auth entry point
- **DingTalk**: planned, not ready

#### E. Trust is not explicitly tiered by channel

Today, the system has roles, but not a clear model for the fact that:

- WeCom employee identity can be stronger than Telegram identity
- Telegram identity can be stronger than anonymous web guest access
- WeChat Official Account follow/openid is useful, but not sufficient for high-risk actions by default

---

## 3. Core design principle

Nexus should use:

## **One Nexus principal, many external channel bindings**

This means:

- a user has one canonical Nexus identity
- that Nexus identity may be linked to multiple external identities
- external identities are entry points, not the final authority for permissions

### 3.1 Canonical objects

#### Nexus Principal

The canonical internal user identity.

Responsible for:

- role
- policy
- audit ownership
- household / organization membership
- long-term permissions

#### Channel Binding

A verified link from an external identity to the Nexus principal.

Examples:

- Telegram: `telegram_user_id`
- WeCom: `corp_id + userid`
- Feishu: `open_id` or equivalent provider identifier
- WeChat Official Account: `openid`
- WeChat Open Platform: `unionid` when available

#### Session / Access Grant

The temporary authenticated access created after a verified entry.

This should record:

- channel
- auth method
- trust level
- issue time / expiry
- resulting Nexus principal

---

## 4. Trust tiers

Not all channels should be treated equally.

### Tier A — organization-verified identity

Use when the platform identity is backed by an organization-managed directory or tenant.

Examples:

- WeCom internal employee identity (`corp_id + userid`)
- future enterprise SSO or trusted org login

Typical capability:

- can map directly to employee principal
- can enter normal authenticated workflows with fewer extra steps
- still may require step-up confirmation for dangerous actions

### Tier B — channel-verified personal identity

Use when the platform strongly identifies a stable user account, but not necessarily an organization member.

Examples:

- Telegram user ID
- Feishu external account identity
- personal messaging identities

Typical capability:

- can bind to an existing Nexus principal
- can act as a legitimate logged-in channel after binding
- should not automatically imply enterprise membership or high privilege

### Tier C — bootstrap / guest identity

Use when the platform offers a reachable identity but not enough proof for privileged access.

Examples:

- WeChat Official Account `openid`
- first contact from a low-trust channel
- unauthenticated web entry

Typical capability:

- onboarding
- invite acceptance
- bind request
- help / documentation / very low-risk actions
- not enough for privileged Home Assistant control or system administration by default

---

## 5. Channel positioning

### 5.1 Telegram

**Role in product:** lowest-friction self-serve and operator channel.

Strengths:

- fast onboarding
- good bot UX
- deep-link support
- good fit for self-hosted/mobile-first usage

Limitations:

- not organization-native
- identity is stable, but not enterprise-authoritative

Recommended usage:

- keep as the best self-serve and admin/operator bind channel
- support deep-link bind and web handoff
- treat Telegram as a linked identity, not the default enterprise trust root

### 5.2 Web

**Role in product:** fallback interface, admin console, and identity handoff surface.

Strengths:

- useful for recovery and management
- useful for QR/device-code style auth handoff
- necessary for admin web capabilities

Limitations:

- current API-key login is too technical for general users
- not yet unified with messaging binding

Recommended usage:

- make web the fallback and linking surface
- not the only primary entry point for normal users

### 5.3 WeCom (Enterprise WeChat)

**Role in product:** preferred enterprise identity path.

Strengths:

- strongest enterprise identity among the discussed chat channels
- better fit for RBAC, org membership, and audit
- lower friction for employees already inside a tenant

Limitations:

- requires org/admin setup
- domain/app visibility constraints
- not suitable as the only family-facing access path

Recommended usage:

- enterprise default auth channel
- map WeCom identity directly to Nexus principal when org-managed

### 5.4 WeChat Official Account

**Role in product:** low-friction China-facing bootstrap channel.

Strengths:

- very low barrier to first contact
- natural mobile entry for family/non-technical users in China
- good for discovery, onboarding, and follow-up prompts

Limitations:

- default identity is `openid`, scoped to the service account
- following or messaging the account is not enough proof for high-trust access
- `unionid` needs additional Open Platform setup and availability conditions

Recommended usage:

- allow guest/bootstrap entry
- use H5/menu-driven linking flows
- require explicit linking, invite, or approval before granting sensitive capabilities

### 5.5 Feishu

**Role in product:** secondary enterprise/workflow channel.

Current state:

- backend/channel support exists
- productized binding/onboarding is still weaker than Telegram

Recommended usage:

- align it to the same binding/session model as WeCom and Telegram later

---

## 6. Recommended unified model

### 6.1 Authentication should be split into three concerns

#### A. Entry authentication

How Nexus confirms the external channel identity for this session.

Examples:

- Telegram deep-link bind or Login Widget
- WeCom OAuth
- Official Account H5 OAuth
- web session login or device-code confirmation

#### B. Identity linking

How the external identity becomes associated with a Nexus principal.

This is where:

- bind tokens
- invite codes
- approval flows
- admin review
- household membership confirmation

should live.

#### C. Authorization

What the resulting Nexus principal is allowed to do.

This should depend on:

- role
- policy
- trust tier
- action risk
- possibly household/org scope

---

## 7. Recommended user flows

### 7.1 Telegram flow

Best near-term flow:

1. user clicks Telegram deep link or starts bot
2. if already linked, enter normal conversation flow
3. if not linked, user gets one of:
   - bind token flow
   - invite code flow
   - web handoff flow
4. after successful linking, Telegram becomes a bound channel for that principal

### 7.2 Web fallback flow

Recommended direction:

1. user opens web UI
2. if already authenticated, continue
3. if not authenticated, offer:
   - existing admin/dev login path
   - link via Telegram
   - link via WeCom
   - future China-friendly link via Official Account
4. web session is created only after server-side verified handoff

This should evolve toward a **device-code / handoff model**, not just API keys for normal users.

### 7.3 WeCom flow

Recommended enterprise flow:

1. user opens Nexus from WeCom
2. WeCom OAuth identifies `corp_id + userid`
3. system maps this identity to a Nexus principal
4. if mapping exists, log in directly
5. if mapping does not exist, enter approval / first-bind flow

### 7.4 WeChat Official Account flow

Recommended bootstrap flow:

1. user follows or messages the Official Account
2. system routes user into OA H5 auth and gets `openid`
3. if user is unknown, create guest/bootstrap session only
4. offer:
   - invite code
   - family binding code
   - web handoff
   - admin approval path
5. only after explicit linking should the user receive stronger access

---

## 8. What should not be done

### Do not treat raw channel identity as full authorization

Bad examples:

- giving admin rights because a user followed a WeChat Official Account
- granting privileged access from Telegram username alone
- trusting unsigned web/chat payloads

### Do not duplicate auth logic per channel forever

Each new channel should not invent its own role model and bind semantics.

Instead, each channel should plug into:

- the same principal model
- the same binding ledger
- the same trust tier policy
- the same audit event format

### Do not force web to be the main path for everyone

The product direction is messaging-first and mobile-first.

Web should be:

- a fallback
- a management surface
- a handoff surface

not the only normal-user entry path.

---

## 9. Proposed phased implementation plan

### Phase 1 — unify the model first

Before adding new channels, define and implement:

- Nexus principal vs channel binding terminology
- trust tier evaluation
- session/auth event schema
- rules for what guest / linked / full-trust users can do

**This should happen before implementing WeCom or Official Account onboarding.**

### Phase 2 — unify Telegram + web

Near-term implementation priority:

- keep Telegram as the current best low-friction channel
- reduce bind-token friction where possible
- make web a real fallback / handoff surface
- move away from API-key-only mindset for normal-user web access

This is the highest-value next implementation slice after the current Telegram fixes.

### Phase 3 — add WeCom as primary enterprise entry

Implement:

- WeCom identity callback
- principal mapping
- org-aware trust tier
- audit events

This should be the first major new channel for enterprise-grade low-friction access.

### Phase 4 — add WeChat Official Account as bootstrap channel

Implement:

- guest/bootstrap entry
- OA H5 link handoff
- invite/bind/approval flow

This should optimize for low entry friction, not immediate high privilege.

### Phase 5 — align Feishu and later channels

After the unified model is stable:

- bring Feishu to the same onboarding/session model
- evaluate DingTalk later

---

## 10. Recommended near-term decision

If only one auth architecture decision is made now, it should be this:

## **Nexus should standardize on one principal with multiple bound channel identities and explicit trust tiers.**

Then channel strategy becomes:

- **Telegram** = best self-serve/mobile operator channel
- **Web** = fallback + management + identity handoff surface
- **WeCom** = preferred enterprise identity channel
- **WeChat Official Account** = low-friction bootstrap channel for China-facing access

This matches the current product direction better than expanding the current Telegram-specific bind-token model to every channel.

---

## 11. Suggested next implementation document

The next useful follow-up should be a more concrete execution spec, for example:

- `docs/auth_binding_state_machine.md`

That document should define:

- principal schema additions if needed
- binding states (`pending`, `verified`, `revoked`, `guest-only`)
- trust tier rules
- auth audit event schema
- Telegram/web handoff flow
- WeCom first-bind flow
- Official Account bootstrap flow
