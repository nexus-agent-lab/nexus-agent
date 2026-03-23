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

## Recent Decision
- For now, keep first-run setup simple:
  - configure `.env`
  - launch the stack
  - read initial admin credentials from backend logs
  - optionally configure Telegram afterwards
- Defer bootstrap/setup UI until real setup pain is better validated.
- Treat WeChat as a strategically important family-facing entry candidate, but only after current setup and post-bootstrap flows are validated.

## Next Action
Priority queue from here:
1. Validate the current docs-first first-run flow end-to-end:
   - minimal `.env`
   - initial admin from logs
   - web login
   - optional Telegram setup and bind
2. Validate the Home Assistant core loop and identify the highest-friction real daily-use failures.
3. Reassess whether WeChat should become the next major entry-path spike after those validations.
