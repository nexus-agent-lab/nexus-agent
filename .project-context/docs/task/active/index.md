# Active Task Index

## Goal
Keep advancing the active P0-2 auth/ingress thread while also capturing architecture decisions that shape the skill, worker, and learning stack.

## Current State
- Browser/MCP session architecture direction is now clarified:
  - Playwright should remain a built-in, public, stateless, read-only browser plugin in the near term
  - future authenticated browser usage should move to Nexus-managed per-user MCP sessions rather than shared MCP-side state
  - this session-isolation design should be generalized for future identity-bearing MCP plugins, not implemented as a Playwright-only special case
- Web Browser MCP transport registration has been repaired at the connection layer:
  - `app/core/mcp_manager.py` now supports both legacy SSE and streamable HTTP (`/mcp`) transports
  - the remote MCP connection now sends a normalized `Host` header so container-to-container `/mcp` requests are accepted by the current Playwright MCP host check
  - the Web Browser plugin can now connect and register its Playwright toolset instead of falling back to `python_sandbox`
  - verified registered browser tools now include `browser_navigate`, `browser_snapshot`, `browser_take_screenshot`, `browser_wait_for`, and the rest of the 22-tool Playwright set
- Web browsing skill metadata has been realigned to the actual registered Playwright tool names:
  - replaced stale `browser_extract` / `browser_screenshot` requirements with `browser_snapshot` / `browser_take_screenshot`
- The repo now has current planning docs for:
  - entry/binding loop: `docs/architecture/p0_entry_binding_loop_estimate.md`
  - implementation milestones: `docs/architecture/p0_entry_binding_loop_implementation_plan.md`
  - WeChat channel integration: `docs/architecture/wechat_channel_integration_plan.md`
  - future bootstrap direction: `docs/architecture/bootstrap_owner_flow.md`
  - local-model benchmark subsystem direction: `docs/architecture/local_model_benchmark_subsystem.md`
- A minimum useful local-model benchmark subfunction now exists:
  - benchmark module scaffold under `app/benchmarks/`
  - versioned benchmark suite under `app/benchmarks/scenarios/suite_v1/`
  - deterministic fixture tools for stable tool-selection / response-quality / error-rate evaluation
  - CLI entrypoint at `scripts/run_local_model_benchmark.py`
  - JSON and Markdown benchmark archive outputs under `benchmark_results/`
  - local-direct Ollama execution behavior for fairness:
    - no Docker model runtime
    - serial one-model-at-a-time execution
    - warmup before measured runs
    - unload loaded models before switching
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
- The admin user-management UI now exposes channel binding state more directly:
  - the users table now loads Telegram/WeChat state from a dedicated admin summary endpoint instead of overloading `GET /users/`
  - the users table shows Telegram/WeChat bound state inline
  - the WeChat detail card no longer shows the default bind CTA once the user is already connected, and offers reconnect instead
- The web admin now has a first-pass frontend locale layer:
  - a dedicated `/language` page switches the admin UI between English and Chinese
  - locale is stored in a browser cookie and currently drives sidebar/navigation plus the users page
- Runtime security defaults have been hardened:
  - `JWT_SECRET` is now resolved dynamically instead of freezing a short import-time default
  - `JWT_SECRET` and `NEXUS_MASTER_KEY` auto-generate and persist on startup if missing or invalid
  - WeChat user tokens can now be encrypted without manual first-run secret setup
- Admin web session-recovery behavior is now tighter:
  - client-side integrations/admin fetches no longer stop at a `401` toast
  - expired-session paths now clear the `access_token` cookie and send the browser back to `/login`
- Admin web sessions now use sliding renewal:
  - base token lifetime remains 24 hours
  - the web app refreshes the session before expiry while the app stays in active use

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
- Treat frontend `401` handling as a session-recovery concern, not just a notification concern:
  - show the error
  - clear the stale session
  - return the user to sign-in
- Treat session lifetime as sliding rather than hard-expiring during normal active admin use.
- Treat local-model selection as an agent-runtime benchmarking problem, not a single-turn chat comparison problem:
  - use one versioned benchmark suite
  - keep prompts/tasks fixed across models
  - archive raw run artifacts for later comparison

## Next Action
Priority queue from here:
1. Convert the browser architecture note into an implementation plan:
   - add Playwright tool-group policy for read / interact / sensitive / runtime buckets
   - keep the first phase public, stateless, and read-only
   - define the minimal `MCPSessionManager` contract for future `scope=user` session isolation across MCP plugins
2. Finish the Playwright browser runtime validation path:
   - rerun the minimal browser smoke test against `https://s.weibo.com/top/summary`
   - confirm the end-to-end agent path now selects the registered Web Browser tools instead of `python_sandbox`
3. Run a real-device WeChat validation pass for:
   - admin user detail page QR modal opens and shows the returned image/url
   - QR scan completes and stores a per-user bot token
   - poll loop starts for the bound user
   - inbound text receipt resolves to the correct bound Nexus user
   - outbound reply delivery works through the correct per-user WeChat session
4. Verify after restart that auto-generated `JWT_SECRET` / `NEXUS_MASTER_KEY` persist and the previous runtime warnings are gone.
5. Fold any protocol mismatches from the real iLink payloads back into `app/interfaces/wechat.py`.
6. Manually validate sliding-session behavior in the browser:
   - confirm refresh happens before the 24-hour token expiry window
   - confirm background/visibility transitions do not break the next refresh
7. Manually validate the expired/revoked-token browser path on admin integrations pages and confirm the user is redirected to `/login` instead of staying on the page after the toast.
8. After the transport is confirmed, decide whether the next WeChat increment is:
   - WeChat unbind / runtime teardown UX
   - richer admin visibility for per-channel health and last-seen state
   - richer message support
9. If local-model benchmarking becomes active work, implement Phase 1 of `docs/architecture/local_model_benchmark_subsystem.md` as a sidecar subsystem:
   - versioned scenarios
   - deterministic fixture tools
   - config-driven model manifest
   - archived JSON benchmark results
10. For the benchmark subsystem next, tighten the evaluation fidelity:
   - reuse more of the real LangGraph path instead of the current light benchmark loop
   - improve response-quality grading beyond substring rules
   - add a first real benchmark batch for the local models currently under consideration
