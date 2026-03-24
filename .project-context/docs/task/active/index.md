# Active Task Index

## Goal
Keep advancing the active P0-2 auth/ingress thread while also capturing architecture decisions that shape the skill, worker, and learning stack.

## Current State
- The repo now has current planning docs for:
  - entry/binding loop: `docs/architecture/p0_entry_binding_loop_estimate.md`
  - implementation milestones: `docs/architecture/p0_entry_binding_loop_implementation_plan.md`
  - WeChat channel integration: `docs/architecture/wechat_channel_integration_plan.md`
  - future bootstrap direction: `docs/architecture/bootstrap_owner_flow.md`
- Product direction has been re-aligned toward a docs-first first-run flow rather than implementing a bootstrap UI immediately.
- The admin web surface no longer uses `X-API-Key` inside `web/src`; audit, cortex, users, and integrations pages now use bearer auth consistently in the JWT-backed admin flow.
- The current P0 slice now also has improved denied/recovery wording plus structured auth/policy audit events for bind/login/denied flows.
- A first-pass WeChat Phase 1 adapter is now implemented and committed:
  - QR login / bot-token bootstrap
  - `getupdates` polling
  - inbound text normalization into MQ
  - outbound text replies plus typing state
  - worker-side bind command compatibility for `bind 123456` as well as `/bind 123456`
- The WeChat model has now been re-aligned from a legacy single-bot assumption to a user-level ClawBot binding flow:
  - WeChat no longer depends on chat-side `/bind`
  - admin user detail pages now expose a QR-based WeChat binding flow
  - backend WeChat runtime now supports per-user bot-token sessions loaded from user-scoped secrets
  - inbound WeChat messages can resolve directly to the target Nexus user via `msg.user_id`
- Runtime security defaults have been hardened:
  - `JWT_SECRET` is now resolved dynamically instead of freezing a short import-time default
  - `JWT_SECRET` and `NEXUS_MASTER_KEY` auto-generate and persist on startup if missing or invalid
  - WeChat user tokens can now be encrypted without manual first-run secret setup

## Recent Decision
- For now, keep first-run setup simple:
  - configure `.env`
  - launch the stack
  - read initial admin credentials from backend logs
  - optionally configure Telegram afterwards
- Defer bootstrap/setup UI until real setup pain is better validated.
- Treat WeChat as a strategically important family-facing entry candidate, but only after current setup and post-bootstrap flows are validated.
- Move WeChat forward as the next concrete channel spike now that the current Telegram/admin/P0 fixes have settled cleanly in manual testing.
- Treat Telegram and WeChat differently at the product layer:
  - Telegram keeps bind/login handoff UX
  - WeChat uses web-initiated QR binding for a specific Nexus user

## Next Action
Priority queue from here:
1. Run a real-device WeChat validation pass for:
   - admin user detail page QR modal opens and shows the returned image/url
   - QR scan completes and stores a per-user bot token
   - poll loop starts for the bound user
   - inbound text receipt resolves to the correct bound Nexus user
   - outbound reply delivery works through the correct per-user WeChat session
2. Verify after restart that auto-generated `JWT_SECRET` / `NEXUS_MASTER_KEY` persist and the previous runtime warnings are gone.
3. Fold any protocol mismatches from the real iLink payloads back into `app/interfaces/wechat.py`.
4. After the transport is confirmed, decide whether the next WeChat increment is:
   - bind UX polish / reconnect UX
   - admin visibility for WeChat channel state
   - richer message support
