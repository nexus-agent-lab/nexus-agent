# P0 Entry and Binding Loop Estimate

## 1. Objective

Estimate the next product-aligned slice for Nexus based on the current direction:

- mobile-first
- messaging-first
- family-usable
- permission-governed
- auditable

The slice to estimate is:

**family-facing entry -> identity binding -> permission-aware Home Assistant action loop -> audit visibility**

This estimate is intentionally narrower than a full multi-channel auth platform. It focuses on the first durable daily-use loop for home usage while preserving the architecture needed for future enterprise expansion.

## 2. Why This Is The Next Thing To Estimate

Based on `docs/project_focus_and_direction.md`, the near-term product priority is not broad platform expansion and not autonomous self-evolution.

The strongest next product bottleneck is:

- normal users still have too much friction entering Nexus
- identity binding is still too Telegram/admin mediated
- the home control loop is useful, but the user journey into it is not yet low-friction enough
- permission-denied and recovery UX still need tightening

This means the highest-value estimate is the end-to-end entry loop, not a backend-only subsystem.

## 3. Product Outcome

The target user experience:

1. A family user enters from a messaging-friendly surface.
2. Nexus recognizes whether the user is unbound, pending, guest-only, or verified.
3. If not yet bound, Nexus provides a low-friction linking path.
4. Once bound, the user can issue common Home Assistant requests.
5. Nexus enforces role/policy constraints.
6. If an action is denied or ambiguous, the recovery path is understandable.
7. Actions and auth transitions are visible to the admin through audit.

## 4. Recommended Scope Boundary

### In Scope

- entry path for one family-facing channel plus existing web fallback
- lower-friction binding flow
- unified binding-state handling in product UX
- permission-denied and recovery messaging
- audit visibility for bind/login/action lifecycle
- validation of the message-to-HA core loop after binding

### Out of Scope

- full enterprise SSO
- full WeCom / WeChat enterprise auth implementation
- generalized multi-tenant access architecture
- full redesign of permission engine
- skill self-evolution implementation
- broad marketplace or plugin onboarding work

## 5. Candidate Delivery Shapes

There are three realistic cuts.

### Option A: Tighten Telegram + Web Only

Work:

- improve Telegram onboarding
- simplify bind flow
- improve web fallback and handoff
- improve denied/recovery UX

Pros:

- lowest delivery risk
- builds on existing productized path
- fastest time to a usable family loop

Cons:

- does not solve the "Telegram may not be the best family-facing channel" concern

### Option B: Add One New Family-Facing Entry Surface

Work:

- keep Telegram + web
- add one easier family-facing channel entry
- still keep the same principal/binding model

Pros:

- better aligned with direction doc
- validates whether family usage improves materially

Cons:

- higher channel-integration uncertainty
- can dilute focus if the new channel is immature

### Option C: Build Generic Multi-Channel Binding Framework First

Work:

- formalize channel trust tiers
- build generalized binding/session layer
- postpone end-user polishing until later

Pros:

- architecturally clean

Cons:

- too infrastructure-heavy for current product stage
- high chance of delaying real user validation

## 6. Recommendation

Recommended next estimate target:

**Option A as the committed slice, with Option B framed as an explicit follow-up decision gate.**

Reason:

- it aligns with the current repository reality
- it is the fastest path to a family-usable loop
- it still supports later multi-channel generalization
- it avoids overcommitting before user behavior is validated

## 7. Work Breakdown Structure

### 7.1 Workstream A: Entry and Onboarding UX

Goal:

- make unbound and first-run entry understandable for non-technical users

Likely tasks:

- refine unbound-user messaging in Telegram
- refine first bound-user landing flow
- add clearer "what you can do next" messaging
- improve login fallback copy in web
- ensure the channel/web handoff does not feel like an admin workflow

Complexity:

- low to medium

Primary dependencies:

- existing Telegram bind/login flow
- web fallback pages

### 7.2 Workstream B: Binding Flow Simplification

Goal:

- reduce manual token friction while preserving control

Likely tasks:

- tighten deep-link bind flow
- simplify token presentation and exchange
- unify state handling for `pending`, `verified`, `guest_only`, and `revoked`
- make rebind/unbind behavior clearer

Complexity:

- medium

Primary dependencies:

- `AuthService`
- `UserIdentity`
- bind token lifecycle
- current Telegram/web auth handoff

### 7.3 Workstream C: Permission-Denied and Recovery UX

Goal:

- make failures actionable instead of vague

Likely tasks:

- improve permission-denied copy
- explain when an admin is required
- improve entity-not-found / clarification prompts
- improve retry vs stop behavior wording

Complexity:

- low to medium

Primary dependencies:

- `ResultClassification`
- reviewer / skill-worker follow-up paths
- existing HA runtime guardrails

### 7.4 Workstream D: Audit Visibility

Goal:

- make auth and action flows inspectable by the operator/admin

Likely tasks:

- define auth lifecycle audit event names
- record bind start / bind success / bind revoke / login handoff completion
- record denied high-risk action attempts
- expose a minimum useful view in existing admin surfaces

Complexity:

- medium

Primary dependencies:

- current audit model
- auth and action execution paths

### 7.5 Workstream E: P0 Validation

Goal:

- prove the loop works for normal daily usage

Likely tasks:

- validate entry from unbound user
- validate bind completion
- validate first successful Home Assistant action
- validate permission-denied message
- validate audit trail presence

Complexity:

- medium

Primary dependencies:

- HA validation checklist
- messaging/web test flows

## 8. Suggested Delivery Sequence

The best execution order:

1. Entry/onboarding UX
2. Binding flow simplification
3. Permission-denied and recovery UX
4. Audit event coverage
5. End-to-end validation

This order matters because audit without a polished flow does not unblock users, and new entry points before fixing the core bind loop will multiply rough edges.

## 9. Estimate By Slice

This estimate assumes one focused implementation pass by a contributor who already understands the codebase.

### Option A: Telegram + Web tightening

- discovery / final scope shaping: 0.5 to 1 day
- entry/onboarding UX: 1 to 2 days
- binding simplification: 1.5 to 3 days
- permission/recovery UX: 1 to 2 days
- audit coverage and admin visibility: 1 to 2 days
- validation and polish: 1 to 2 days

Estimated total:

- **6 to 12 working days**

### Option B: add one new family-facing entry surface after Option A

- channel integration spike: 2 to 4 days
- identity mapping/bind UX for that channel: 2 to 4 days
- policy/audit integration: 1 to 2 days
- validation and polish: 1 to 2 days

Additional estimate:

- **6 to 12 working days**

### Option C: generic multi-channel framework first

- auth/session model refactor: 3 to 6 days
- generalized binding-state model: 2 to 4 days
- audit/event model expansion: 1 to 3 days
- migration and UX backfill: 3 to 6 days
- validation: 2 to 3 days

Estimated total:

- **11 to 22 working days**

This is why Option C is not recommended as the immediate next slice.

## 10. Risk Areas

### Product Risk

- over-investing in infrastructure before family usage is validated
- adding a new channel before the current bind loop is comfortable

### Technical Risk

- auth state semantics become scattered across Telegram, web, and backend services
- bind token and login handoff logic diverge instead of converging
- audit events stay generic and become hard to reason about later

### UX Risk

- non-technical users still see too much operator language
- permission-denied responses do not clearly tell users what to do next
- fallback to web still feels like a developer recovery path

## 11. Concrete Definition of Done

This slice should be considered done when:

- an unbound family user can enter from the chosen messaging path and understand the next step
- binding completion feels low-friction and reliable
- a bound user can complete at least one common Home Assistant request end-to-end
- denied or ambiguous requests produce understandable recovery guidance
- auth and action transitions are visible in audit
- the loop is validated with a short checklist, not just unit coverage

## 12. What Needs Estimation Detail Next

If we proceed, the next planning artifact should not be another strategy doc. It should be an implementation estimate with file-level impact.

Recommended next estimate breakdown:

1. Telegram/web entry UX changes
2. bind-token and handoff flow changes
3. auth-state and audit event model changes
4. admin surface changes for visibility
5. validation checklist and test coverage

## 13. Proposed Decision

Proceed with estimating and scoping:

**P0 Entry Loop Tightening (Telegram + Web fallback first)**

and treat:

**new family-facing channel exploration**

as a separate go/no-go decision after the Telegram/web loop is comfortable enough for real family usage.
