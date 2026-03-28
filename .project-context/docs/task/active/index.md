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
- The current browser-selection failure has been narrowed to skill routing recall rather than MCP transport:
  - the Web Browser MCP plugin now registers successfully
  - but `route_skills()` still embeds only one synthesized vector per skill
  - natural browser/research requests such as “最新 AI 论文” can therefore miss `web_browsing`
  - a new architecture note now recommends multi-anchor skill recall backed by local Postgres + pgvector
- High-value skills now have curated routing examples for better semantic recall:
  - `web_browsing`, `homeassistant`, `python_sandbox`, `cron_scheduler`, `memory_management`, and `system_management` now include `routing_examples`
  - `SkillLoader` now parses full YAML frontmatter correctly, including multiline lists
  - routing-only metadata is stripped from the prompt-injected skill content, so these examples do not consume LLM context
  - current implementation improves the in-process skill embedding index; pgvector persistence is still the next step
- Skill registration/unregistration behavior is now closer to runtime-safe:
  - `SkillLoader.refresh_runtime_skill_registry()` can rebuild the in-process skill routing index after skill file changes
  - saving/deleting skills via `/api/skills` now refreshes the runtime skill index immediately
  - Telegram `/skill install` and `/skill uninstall` now also refresh the runtime skill index on success
  - plugin deletion now resolves bundled skills from `plugin_catalog.json`, removes unreferenced skill files, and refreshes runtime skill routing to avoid ghost matches
- Skill routing anchors are now persisted to the local Postgres + pgvector stack:
  - new `SkillRoutingAnchor` SQLModel stores `description`, `keyword`, and `routing_examples` anchors with embeddings
  - `register_skills()` now syncs current skill anchors into pgvector and prunes removed skills
  - `route_skills()` now prefers pgvector anchor recall with skill-level aggregation, and falls back to the old in-memory skill index if DB lookup fails
  - this means `routing_examples` now survive reloads and participate in startup-time matching from durable storage
- A dedicated routing-example generation path now exists on the backend:
  - `POST /api/skills/generate-routing-examples`
  - backed by a separate prompt in `app/core/skill_generator.py`
  - intended for MCP/skill registration flows so the UI can generate candidate routing examples without mixing them into the LLM prompt
- Runtime LLM configuration is now more explicit and UI-manageable:
  - the admin backend now exposes `GET/POST /admin/llm-config`
  - main agent LLM and skill-generation LLM can be configured separately
  - dedicated skill-generation config falls back field-by-field to the main agent LLM when left blank
  - the admin web now includes `/llm` for editing these settings without hand-editing `.env`
- The admin Integrations "View Skill" path is now aligned with the rest of plugin catalog resolution:
  - `GET /api/plugins/{id}/skill` and `GET /api/plugins/{id}/schema` no longer require `manifest_id`
  - both endpoints now fall back to matching `plugin_catalog.json` by `source_url`, just like plugin install/delete already did
  - this fixes the case where installed plugins can work normally but the UI fails to open their associated skill content
- The admin Integrations browser-side fetch path is now same-origin safe:
  - integrations client components no longer depend on `http://localhost:8000/api` in the browser
  - a new `web/src/lib/client-api.ts` helper normalizes client fetches to `/api` when the configured public URL points at localhost
  - `docker-compose.yml` now exports `NEXT_PUBLIC_API_URL=/api` for the web service
  - this fixes catalog/schema/skill fetch failures when the UI is accessed from another device, hostname, or reverse-proxy address
- The repo now has current planning docs for:
  - entry/binding loop: `docs/architecture/p0_entry_binding_loop_estimate.md`
  - implementation milestones: `docs/architecture/p0_entry_binding_loop_implementation_plan.md`
  - WeChat channel integration: `docs/architecture/wechat_channel_integration_plan.md`
  - future bootstrap direction: `docs/architecture/bootstrap_owner_flow.md`
  - local-model benchmark subsystem direction: `docs/architecture/local_model_benchmark_subsystem.md`
  - skill routing anchor recall direction: `docs/architecture/skill_routing_anchor_recall_with_local_vector_db.md`
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
- A new chat continuity architecture note now documents the session-context gap and proposed fix:
  - `docs/architecture/session_context_continuation_plan.md`
  - current root cause is that web `/api/chat` and `/api/chat/stream` define `thread_id` but do not resolve or reuse `SessionManager` history
  - recommended P0 fix is to make web chat reuse the same session bootstrap pattern already used by message-channel flows
- The web chat continuity P0 fix is now implemented:
  - new shared bootstrap helper at `app/core/chat_session_bootstrap.py`
  - `/api/chat` and `/api/chat/stream` now resolve `thread_id`, rebuild context from stored summaries plus recent turns, and return canonical `thread_id`
  - incoming user turns are now persisted into session history before graph execution so follow-up turns can see prior user phrasing as well as assistant replies
  - `app/core/worker.py` now reuses the same bootstrap helper to keep web and message-channel context assembly aligned
- The current summary/compaction behavior is now documented for later optimization:
  - `docs/architecture/session_context_summary_current_behavior.md`
  - records when `PREVIOUS CONTEXT SUMMARY` is injected, when compaction is triggered, what roles are included, and the current limits/tradeoffs
- Docker builds now support configurable package mirrors without changing Dockerfiles:
  - root `Dockerfile` only exposes Python `pip` mirror settings because that image does not run `apt`
  - `web/Dockerfile` exposes Alpine `apk` and `npm` mirror settings because those are used during the web image build
  - `docker-compose.yml` and `docker-compose.test.yml` pass only the mirror-related build args that the target image actually uses
- The legacy Streamlit dashboard/runtime path has now been removed from the repo:
  - old `dashboard/` code, Streamlit dependency, and dashboard-only tests/debug scripts were deleted
  - the active admin UI is the Next.js web app under `web/`
  - sandbox file output still uses `/app/storage/sandbox_data`, which maps to the repo-root `storage/sandbox_data` path inside containers

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
- Treat conversation continuity as a backend session-contract problem rather than a frontend prompt-stitching problem:
  - `thread_id` should map to `Session.session_uuid`
  - the backend should return canonical `thread_id` values and rebuild context from stored summaries plus recent raw turns
- Treat user-turn persistence as part of the session contract:
  - if a turn should be resumable later, the current human message must be stored before graph execution
- Treat the current browser tool-miss as a routing-quality problem:
  - do not keep debugging MCP transport when browser tools are already registered
  - improve skill recall by adding multi-anchor routing examples and durable vector recall
- Prefer the existing Postgres + pgvector stack as the local routing vector store:
  - it matches the current repo foundations
  - it is lower-friction than adding a second vector system
- Treat Docker build mirrors as configurable infra defaults rather than hard-coded one-offs:
  - keep Dockerfiles on official upstream defaults
  - let operators opt into mainland mirrors by editing only `.env`

## Next Action
Priority queue from here:
1. Convert the browser architecture note into an implementation plan:
   - add Playwright tool-group policy for read / interact / sensitive / runtime buckets
   - keep the first phase public, stateless, and read-only
   - define the minimal `MCPSessionManager` contract for future `scope=user` session isolation across MCP plugins
2. Convert the skill-routing anchor-recall note into an implementation plan:
   - extend skill metadata with `routing_examples`
   - add pgvector-backed `skill_routing_anchor` storage
   - aggregate top anchor hits back to skills inside `route_skills()`
   - start with `web_browsing` as the first high-value skill
3. Validate the new pgvector-backed skill recall end to end:
   - confirm the `skill_routing_anchor` table is populated on startup
   - verify `web_browsing` now matches natural queries like “最新 AI 论文”
   - confirm uninstall/delete prunes both file-backed skills and their routing anchors
4. Wire the new routing-example generation API into the admin integrations/skill UI:
   - let MCP/skill registration generate editable candidate examples
   - persist accepted examples into skill metadata and into `skill_routing_anchor`
   - show clear copy that these examples affect routing only, not prompt context
5. Manually validate the admin Integrations page against the previously failing plugin row:
   - reopen "View Skill"
   - confirm the skill content and routing examples render
   - confirm plugins created from older rows without `manifest_id` now behave the same as freshly installed catalog plugins
6. Rebuild and restart the web stack once so the updated public client env is applied:
   - the compose-side `NEXT_PUBLIC_API_URL` value changed to `/api`
   - then re-check catalog loading and the "View Skill" modal from the real browser entry URL
7. Extend the new LLM settings surface if needed:
   - decide whether embeddings should get a parallel settings block next
   - decide whether API keys should remain plain editable or move behind the secret store later
8. Finish the Playwright browser runtime validation path:
   - rerun the minimal browser smoke test against `https://s.weibo.com/top/summary`
   - confirm the end-to-end agent path now selects the registered Web Browser tools instead of `python_sandbox`
7. Run a real-device WeChat validation pass for:
   - admin user detail page QR modal opens and shows the returned image/url
   - QR scan completes and stores a per-user bot token
   - poll loop starts for the bound user
   - inbound text receipt resolves to the correct bound Nexus user
   - outbound reply delivery works through the correct per-user WeChat session
8. Verify after restart that auto-generated `JWT_SECRET` / `NEXUS_MASTER_KEY` persist and the previous runtime warnings are gone.
9. Fold any protocol mismatches from the real iLink payloads back into `app/interfaces/wechat.py`.
10. Manually validate sliding-session behavior in the browser:
   - confirm refresh happens before the 24-hour token expiry window
   - confirm background/visibility transitions do not break the next refresh
11. Manually validate the expired/revoked-token browser path on admin integrations pages and confirm the user is redirected to `/login` instead of staying on the page after the toast.
12. Manually validate the new chat continuity contract end-to-end in the real web UI:
   - first send returns a `thread_id`
   - second send with the same `thread_id` retains prior context
   - stream clients correctly consume the initial `session` SSE event
13. After the transport is confirmed, decide whether the next WeChat increment is:
   - WeChat unbind / runtime teardown UX
   - richer admin visibility for per-channel health and last-seen state
   - richer message support
14. If local-model benchmarking becomes active work, implement Phase 1 of `docs/architecture/local_model_benchmark_subsystem.md` as a sidecar subsystem:
   - versioned scenarios
   - deterministic fixture tools
   - config-driven model manifest
   - archived JSON benchmark results
15. For the benchmark subsystem next, tighten the evaluation fidelity:
   - reuse more of the real LangGraph path instead of the current light benchmark loop
   - improve response-quality grading beyond substring rules
   - add a first real benchmark batch for the local models currently under consideration
16. If build performance or reliability on mainland networks remains a concern, run a fresh `docker compose build` validation for `nexus-app` and `web` using the new mirror defaults.
