# WeChat Channel Integration Plan

## 1. Goal

Integrate Tencent iLink / OpenClaw WeChat personal-account bot capability into Nexus as a first-class messaging channel.

Target outcome:

- a user can message Nexus through WeChat
- Nexus can recognize the WeChat identity as a channel binding target
- Nexus can route inbound/outbound text through the existing MQ and agent runtime
- the product can evaluate whether WeChat should become the primary family-facing mobile entry

This plan is based on the local reference project:

- `/Users/michael/work/vendor/weixin-ClawBot-API`

Especially:

- [README.md](/Users/michael/work/vendor/weixin-ClawBot-API/README.md)
- [bot.py](/Users/michael/work/vendor/weixin-ClawBot-API/bot.py)
- [weixin-bot-api.md](/Users/michael/work/vendor/weixin-ClawBot-API/weixin-bot-api.md)
- [weixin-openclaw-api-py-docs.md](/Users/michael/work/vendor/weixin-ClawBot-API/weixin-openclaw-api-py-docs.md)

## 2. Why This Matters

`docs/project_focus_and_direction.md` makes the near-term product direction explicit:

- mobile-first
- messaging-first
- family-usable
- lower friction than technical/admin-centric setup

That document also says:

- Telegram can remain a technical channel
- web should be a fallback
- WeChat or another easier family-facing channel should be explored as a higher-priority user entry

So WeChat is not random expansion. It directly maps to the stated P0 direction.

## 3. Key Architectural Observation

This WeChat integration is much closer to Telegram than to a public-account webhook design.

The reference project uses:

- QR-code login
- a bot token
- long-poll `getupdates`
- explicit `sendmessage`
- explicit typing state via `getconfig` + `sendtyping`

That means the Nexus-side integration model can be:

- **poller/adapter based**
- not webhook-first
- not sidecar-only by necessity

This is important because it reduces architectural risk.

## 4. Product Role of WeChat

Recommended role:

- **family-facing primary messaging entry candidate**

Not recommended role:

- enterprise trust root
- high-assurance org identity

Reason:

- the channel identity is stable enough for personal binding
- but it is still a personal WeChat channel, not an organization-managed identity source

So in Nexus terms, WeChat should be treated similarly to Telegram:

- good for home / family scenarios
- good for low-friction daily usage
- not the strongest enterprise trust source

## 5. Current Nexus Fit

The existing codebase already has the right structural hooks:

- `ChannelType.WECHAT` already exists in [mq.py](/Users/michael/work/nexus-agent/app/core/mq.py)
- `InterfaceDispatcher` already uses channel-based outbound handlers in [dispatcher.py](/Users/michael/work/nexus-agent/app/core/dispatcher.py)
- channel binding already has a generic data model via `UserIdentity` in [user.py](/Users/michael/work/nexus-agent/app/models/user.py)
- auth strategy docs already assume multi-channel identity binding

So this is not a greenfield feature. It is a missing adapter plus UX/binding productization.

## 6. Proposed Integration Shape

### 6.1 Minimal Form

Add a new Python interface adapter:

- `app/interfaces/wechat.py`

Responsibilities:

- QR login and bot token lifecycle
- long-poll inbound message monitoring
- conversion from iLink inbound messages to `UnifiedMessage`
- outbound `sendmessage`
- optional typing support

### 6.2 Runtime Flow

```text
WeChat user
  -> iLink getupdates
  -> app/interfaces/wechat.py
  -> MQ inbox
  -> agent/runtime
  -> MQ outbox
  -> app/interfaces/wechat.py
  -> iLink sendmessage
  -> WeChat user
```

### 6.3 Identity Mapping

Use:

- `provider = "wechat"`
- `provider_user_id = from_user_id`

Where `from_user_id` is the stable inbound ID from iLink, typically of the form:

- `xxx@im.wechat`

This should be sufficient for first-phase binding.

## 7. Important Protocol Constraints

From the local reference implementation, the following are mandatory:

### 7.1 Request Headers

Every request must include:

- `AuthorizationType: ilink_bot_token`
- random per-request `X-WECHAT-UIN`
- `Authorization: Bearer <bot_token>` after login

### 7.2 Login

- fetch QR code
- poll login status
- obtain `bot_token`

### 7.3 Long Poll Cursor

- `get_updates_buf` must be persisted in memory during the running session
- it must be updated after each poll result

### 7.4 Reply Context

- every outbound reply must include the current inbound `context_token`
- old tokens cannot be reused

### 7.5 Typing

- `getconfig` is needed to obtain `typing_ticket`
- `typing_ticket` should be cached per user
- `sendtyping(status=1)` before reply
- `sendtyping(status=2)` after reply

### 7.6 First Phase Media Scope

Do not support media first.

Phase 1 should support:

- inbound text
- outbound text
- typing indicator

## 8. Recommended File-Level Changes

### Backend Adapter

- add [wechat.py](/Users/michael/work/nexus-agent/app/interfaces/wechat.py)

Likely contents:

- `run_wechat_bot()`
- `send_wechat_message(msg: UnifiedMessage)`
- login/poll helpers
- message normalization helpers

### Dispatcher

- update [dispatcher.py](/Users/michael/work/nexus-agent/app/core/dispatcher.py)

Changes:

- register and resolve `ChannelType.WECHAT`

### Startup Wiring

Likely update:

- [main.py](/Users/michael/work/nexus-agent/app/main.py)

Changes:

- initialize WeChat adapter lifecycle similarly to Telegram/Feishu if enabled by env

### Configuration

Likely add env/config entries in:

- [config.py](/Users/michael/work/nexus-agent/app/core/config.py)
- `.env.example` if applicable

Possible settings:

- `WECHAT_ENABLED`
- `WECHAT_BOT_TOKEN` or login persistence settings
- `WECHAT_POLL_ENABLED`
- `WECHAT_CHANNEL_VERSION`

### Identity / Binding

Likely update:

- [auth_service.py](/Users/michael/work/nexus-agent/app/core/auth_service.py)
- [telegram.py](/Users/michael/work/nexus-agent/app/interfaces/telegram.py) only if cross-channel wording is unified

Changes:

- support `provider="wechat"` in the same binding APIs and helper methods
- no new binding table required in phase 1

### Audit

Likely update:

- [audit.py](/Users/michael/work/nexus-agent/app/models/audit.py)
- any audit service helpers already used in runtime/auth paths

Suggested event types:

- `channel.wechat.login_started`
- `channel.wechat.login_completed`
- `channel.wechat.message_received`
- `channel.wechat.message_sent`
- `auth.binding_succeeded`
- `policy.action_denied`

## 9. Delivery Phases

### Phase 1: Transport Spike

Goal:

- prove Nexus can receive and send text through iLink

Scope:

- QR login
- getupdates long poll
- inbound text to MQ
- outbound text from outbox

Success criteria:

- send a message from WeChat to Nexus
- receive a Nexus reply in WeChat

### Phase 2: Binding and Identity

Goal:

- make WeChat a real user-facing entry path

Scope:

- `provider="wechat"` binding
- unbound guest messaging
- bind token flow reuse
- menu/onboarding equivalent guidance in WeChat copy

Success criteria:

- an unbound WeChat user gets the right onboarding
- a bound user is recognized consistently across sessions

### Phase 3: UX and Safety

Goal:

- make WeChat usable for daily family interactions

Scope:

- typing polish
- permission-denied clarity
- entity-not-found / clarification copy
- audit visibility

Success criteria:

- WeChat feels comparable to Telegram for the home control loop

### Phase 4: Channel Decision

Goal:

- decide whether WeChat becomes the primary family entry

Decision signals:

- onboarding friction
- family willingness to use it
- reliability versus Telegram
- login/binding pain
- message delivery quality

## 10. Risks

### Product Risk

- building WeChat too early could distract from finishing the current Telegram/web binding loop

### Technical Risk

- bot token lifecycle and QR login persistence may need extra state handling
- reply correctness depends on correct `context_token` handling
- typing flow adds extra protocol surface

### Operational Risk

- the bot identity may change after each QR login
- Tencent may change policy or protocol details
- this should not become the only production entry path until stability is proven

## 11. Priority Recommendation

Based on `docs/project_focus_and_direction.md`, WeChat is strategically important, but the immediate sequencing still matters.

### Recommendation

- **Strategic priority:** high
- **Immediate implementation priority:** after Milestone 1 of the Telegram/web entry-loop plan

That means:

1. do not demote WeChat to P2
2. do not start with full WeChat integration before tightening the current binding model
3. use WeChat as the next major entry-path spike once the shared binding-state and auth-outcome layer exists

## 12. Suggested Updated Priority Order

### P0-A

Finish the shared entry/binding foundation:

- binding-state-aware UX
- shared auth outcome shaping
- Telegram/web entry consistency

### P0-B

Run the WeChat transport spike:

- `app/interfaces/wechat.py`
- inbound/outbound text
- QR login lifecycle

### P0-C

Bind WeChat into the same principal model:

- `provider="wechat"`
- onboarding
- bind token flow
- audit

### P1

Decide whether WeChat replaces Telegram as the primary family-facing messaging entry.

## 13. Proposed Decision

Proceed as follows:

1. keep the current Telegram/web implementation-plan Milestone 1 as the immediate next coding task
2. immediately after that, move WeChat to the front of the queue as the next spike
3. treat WeChat as a serious P0 family-entry candidate, not as a speculative future integration

That is the best fit with the current strategy document and the actual capabilities of the local `weixin-ClawBot-API` reference project.
