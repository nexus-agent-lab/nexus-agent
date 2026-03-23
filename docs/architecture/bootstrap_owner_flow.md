# Bootstrap Owner Flow

## 1. Goal

Define the correct first-run experience for a freshly deployed Nexus instance.

The key product decision is:

**A brand-new deployment should not start with normal login. It should start with a limited bootstrap / owner-claim flow.**

That bootstrap flow should let the deployment owner:

1. access a restricted setup page without prior authentication
2. configure or confirm the primary messaging channel
3. bind their own messaging identity
4. become the initial Nexus administrator
5. then transition the instance into normal authenticated multi-user mode

## 2. Why This Is Needed

The current system still reflects a later-stage multi-user assumption:

- users already exist
- admin creates bind tokens
- users bind external identities
- web login then happens as a normal auth step

That is not the right first-run product story for a self-hosted deployment.

For a real owner installing Nexus at home, the more natural sequence is:

1. deploy the system
2. open Nexus
3. claim the deployment
4. bind their Telegram account
5. become the first admin
6. then manage family members and integrations

This is more consistent with `docs/project_focus_and_direction.md`, which emphasizes:

- mobile-first entry
- family-usable setup
- messaging-first interaction
- admin-managed governance after setup

## 3. Product Principle

Nexus should distinguish two system modes:

### Mode A: Bootstrap Mode

The instance has not been claimed yet.

Properties:

- no normal user authentication required yet
- only a restricted setup surface is available
- only owner-claim actions are allowed
- the goal is to create the first trusted administrator

### Mode B: Normal Mode

The instance has already been claimed.

Properties:

- normal authentication rules apply
- web pages are protected
- messaging identities are linked through standard bind flows
- admins manage other users, groups, and integrations

## 4. The Correct First-Run Story

### 4.1 Fresh Deployment

After deployment, opening the Nexus web URL should not drop the user into the normal login page immediately.

Instead, if the system is unclaimed, the user should be redirected to:

- `bootstrap/setup`

This page is not a public general-purpose page. It is a one-time instance-claim page.

### 4.2 Owner Setup

The page should guide the owner through:

1. confirm system is not yet claimed
2. choose or confirm the primary messaging channel
3. complete owner binding
4. finalize bootstrap

For the current product stage, the best first supported bootstrap channel is:

- Telegram

Later, WeChat may become the more family-natural bootstrap entry.

### 4.3 Owner Binding

The owner should bind their own Telegram identity during bootstrap.

That binding should:

- create or claim the first Nexus principal
- assign that principal the `admin` role
- mark the deployment as bootstrapped

After that point:

- the owner can use Telegram handoff to sign into web
- the owner can use the admin UI to create family members and groups

## 5. Proposed UX Flow

```text
Fresh deploy
  -> open web
  -> system detects bootstrap not complete
  -> show restricted setup page
  -> prompt owner to configure / verify Telegram bot
  -> owner binds Telegram identity
  -> system creates first admin user
  -> bootstrap_complete = true
  -> redirect owner to admin/dashboard
```

## 6. What “No Authentication During Bootstrap” Means

This does **not** mean the whole system is publicly open.

It means:

- the bootstrap page is temporarily accessible only while the instance is unclaimed
- the allowed actions are extremely narrow
- the page exists only to let the first owner claim the deployment

So the security posture is:

- unclaimed instance:
  - restricted setup access
  - no normal app access
- claimed instance:
  - bootstrap route disabled or guarded
  - normal auth rules fully enabled

## 7. Recommended Bootstrap Scope

### In Scope for the First Version

- detect whether bootstrap is complete
- redirect fresh web visits to bootstrap page
- guide owner through Telegram-based claim flow
- create initial admin user
- persist `bootstrap_complete`

### Out of Scope for the First Version

- fully generic channel-agnostic bootstrap wizard
- full WeChat bootstrap implementation
- advanced org setup
- household/group setup wizard
- complete secret-management UI for all integrations

## 8. Telegram’s Role in Bootstrap

For the first version:

- Telegram is the owner-claim channel

This fits current repository maturity because Telegram already has:

- binding logic
- onboarding messages
- login handoff support

So Telegram can act as the first trusted personal channel used to claim the instance.

Important nuance:

- Telegram is not the first *general* admin login
- Telegram is the first *owner bootstrap identity*

After bootstrap, web remains the admin console and Telegram remains a linked channel.

## 9. Proposed State Model

Add a system-level setup state, for example:

- `bootstrap_complete: false | true`

Optional future fields:

- `bootstrap_completed_at`
- `bootstrap_admin_user_id`
- `bootstrap_channel`

This state should be stored centrally, for example in:

- `SystemSetting`

This is better than inferring first-run state from loose heuristics.

## 10. Recommended Owner Claim Logic

### Step 1: Detect Unclaimed Instance

On web request:

- if no bootstrap setting exists, or `bootstrap_complete=false`
- route to bootstrap page instead of normal login

### Step 2: Confirm Telegram Availability

Bootstrap page should check:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`

If missing:

- show setup guidance
- do not continue to claim

### Step 3: Start Owner Bind Flow

Recommended first implementation:

- bootstrap page shows a one-time owner bind token or bind deep-link flow
- owner opens Telegram and binds their own account

Alternative later refinement:

- bootstrap page starts a direct Telegram owner-claim challenge

### Step 4: Create Initial Admin

If there is no existing admin and bootstrap is incomplete:

- create the first `User`
- assign role `admin`
- bind Telegram identity to that user

Or:

- if a pre-created bootstrap user exists, claim that user and promote to `admin`

The cleaner first design is:

- create-on-claim

### Step 5: Seal Bootstrap

After successful owner binding:

- set `bootstrap_complete=true`
- store owner/admin user id
- redirect to normal app/dashboard

## 11. Changes To Existing Login Semantics

This design changes how the login page should be interpreted.

### Before Bootstrap

The regular login page should not be the primary first screen.

Instead:

- redirect to bootstrap

### After Bootstrap

The existing login choices make sense:

- Telegram sign-in for bound users
- API key sign-in for admin/recovery

So `Continue with Telegram` remains valid, but only **after** the system has already been claimed.

## 12. Relationship To Current Plans

This design changes priority ordering.

### Previously

- refine Telegram/web login
- then evaluate WeChat

### Updated

- define and implement bootstrap owner flow first
- then refine post-bootstrap Telegram/web sign-in
- then add WeChat as a stronger family-facing entry

This is a better product order because:

- bootstrap defines the first-run story
- normal auth refinement should sit on top of that story
- WeChat can later plug into the same owner-claim and member-entry framework

## 13. Recommended New Priority Order

### P0-A

Bootstrap owner flow

- system unclaimed detection
- restricted bootstrap page
- Telegram owner claim
- initial admin creation
- bootstrap completion flag

### P0-B

Post-bootstrap auth polish

- Telegram/web sign-in experience
- bind-flow simplification
- clearer recovery paths

### P0-C

WeChat transport spike

- integrate WeChat channel
- evaluate as family-facing primary entry

### P1

Family member onboarding

- invite flow
- member bind flow
- family/group management

## 14. File-Level Impact

### Backend

Likely areas:

- `app/api/auth.py`
- `app/core/auth_service.py`
- `app/models/settings.py`
- `app/api/admin.py` or a new bootstrap route module

### Web

Likely areas:

- add a bootstrap page such as:
  - `web/src/app/bootstrap/page.tsx`
- update root/login routing:
  - `web/src/app/page.tsx`
  - `web/src/app/login/page.tsx`
- possibly middleware/proxy gating:
  - `web/src/middleware.ts`

### Telegram

Likely areas:

- `app/interfaces/telegram.py`

Use:

- bootstrap-aware bind messaging
- maybe dedicated owner-claim token handling

## 15. First Implementation Cut

The lowest-risk first cut is:

1. add bootstrap-complete detection
2. add a restricted bootstrap page
3. require Telegram config to continue
4. complete owner bind using a special bootstrap claim flow
5. create first admin and seal bootstrap

Do not try to solve:

- multi-channel bootstrap
- group creation
- member onboarding

in the same first cut.

## 16. Open Questions

Before implementation, decide:

1. Should bootstrap create the first admin user from scratch, or claim a pre-seeded one?
2. Should the bootstrap page itself generate a one-time owner bind token?
3. Should bootstrap be disabled permanently after completion, or reopenable by filesystem/env override?
4. Should WeChat be introduced only after Telegram bootstrap works, or should bootstrap already be channel-pluggable?

## 17. Proposed Decision

Recommended decision:

- make bootstrap a first-class system mode
- use Telegram as the first owner-claim channel
- create the first admin during bootstrap claim
- only after bootstrap, expose normal login semantics

This is the cleanest product story for a self-hosted Nexus deployment and best matches the project’s home-first, messaging-first direction.
