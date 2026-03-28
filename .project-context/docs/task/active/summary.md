# Summary

## Branch Intent
Advance P0-2 access/auth hardening and resilient ingress. Bearer JWT migration for web/backend is complete; Nginx resilience work was started conceptually but the user independently fixed and committed the Nginx rediscovery issue.

## Current State
- HA tracking baseline exists in `docs/ha_p0_validation_checklist.md` and is linked from `docs/task.md`.
- Auth strategy docs are in place: `docs/auth_channel_strategy.md` and `docs/auth_binding_state_machine.md`.
- Telegram bind UX fix and HA checklist were committed earlier: `59ed1f1`.
- Telegram↔web handoff MVP is implemented and committed:
  - `341e934` Document auth channel strategy
  - `b5abcd1` Add Telegram web login handoff backend
  - `4c116a9` Add Telegram handoff login UI
  - `18d5895` Use local uv checks and retire Streamlit entrypoint
- Bearer JWT hardening is implemented and committed:
  - `41d5b1a` Add bearer token auth support
  - `64476a5` Use bearer auth in web actions
  - `d22d31a` Use bearer auth in web pages
- Current backend auth (`app/core/auth.py`) now accepts both `Authorization: Bearer <JWT>` and legacy `X-API-Key`.
- High-impact Next.js actions/pages were migrated off `payload.api_key` forwarding and now send Bearer token headers via `web/src/lib/server-auth.ts`.
- Verification succeeded after the hardening work:
  - focused auth tests passed
  - `./scripts/dev_check.sh` passed with frontend build success and `157 passed`
- User separately fixed Nginx/backend restart tolerance and committed it as:
  - `1557166` Fix nginx backend rediscovery after compose restarts

## Known Risks
- One unrelated local change remains unstaged/uncommitted: `tests/unit/test_router.py` (hook formatting side-effect). It was intentionally excluded from the auth commits.
- The Nginx todo chain in this session was not completed by me. I inspected current ingress setup and confirmed `docker-compose.yml` already has an `nginx` service pointing at `deploy/nginx/nexus.conf`, but the user stated they fixed Nginx and committed their own change. My planned Nginx implementation/doc/verification steps were therefore superseded and not executed.
- `CLAUDE.md`, `.ai-governance/`, and other local/governance files remain intentionally uncommitted.
- Web still uses decode-only JWT parsing in `web/src/lib/auth.ts` for route/session inspection. Backend is now the real auth authority for API calls, which was the main security goal of this slice.

## Next Action
Decide whether to continue with product-facing P0-2 work (permission-denied / recovery UX) or to explicitly reconcile/close the superseded Nginx todo chain after reviewing the user’s Nginx commit `1557166`.

## Session Update (2026-03-22)
- Added `docs/architecture/autoskill_self_evolution_integration.md` to map the AutoSkill paper onto the current Nexus skill/designer architecture.
- Recommendation from this session:
  - keep `MemSkillDesigner` specialized for `MemorySkill.prompt_template` evolution
  - add a future `SkillEvolutionEngine` that turns normalized runtime failures into typed patch candidates
  - begin with low-risk `append_rule` evolution on existing skill cards rather than full autonomous skill mutation
- Important context discovered while loading project context:
  - `.project-context/docs/task/active/index.md` was missing and has now been recreated
  - `.project-context/docs/task/active/task.md` and `.project-context/docs/task/active/verification.md` are still absent

## Session Update (2026-03-23)
- Committed the AutoSkill architecture note and related project-context updates as `d4be5d0` (`Document autoskill self-evolution integration`).
- That commit also included already-staged repo/governance file updates:
  - `.project-context/install-manifest.yaml`
  - `AGENTS.md`
  - `CLAUDE.md`
  - `GEMINI.md`
  - rename `.agent/workflows/dev-rules.md` -> `.agents/workflows/dev-rules.md`
- After reading `docs/project_focus_and_direction.md`, the recommended next estimation target is not generalized self-evolution. The strongest next estimate is the P0 user entry path:
  - family-facing messaging entry
  - identity binding
  - permission-aware home control loop
  - audit visibility

## Session Update (2026-03-23, follow-up)
- Added `docs/architecture/p0_entry_binding_loop_estimate.md`.
- Recommendation in that estimate:
  - commit to Telegram + web fallback tightening first
  - defer any new family-facing channel to a later explicit decision gate
- Estimated size for the recommended slice:
  - roughly 6 to 12 working days for focused implementation, audit visibility, and validation

## Session Update (2026-03-23, implementation planning)
- Added `docs/architecture/p0_entry_binding_loop_implementation_plan.md`.
- The plan breaks the work into four milestones:
  - binding-state-aware UX
  - bind flow simplification
  - permission-denied and recovery UX
  - audit coverage and admin visibility
- Recommended first engineering task:
  - Milestone 1: shared auth outcome shaping plus clearer Telegram/web onboarding and state handling

## Session Update (2026-03-23, WeChat planning)
- Read the local `vendor/weixin-ClawBot-API` reference project.
- Important finding:
  - this WeChat path is not a webhook/public-account-only design; it uses QR login + bot token + long-poll `getupdates`, which makes it architecturally much closer to Telegram than initially assumed
- Added `docs/architecture/wechat_channel_integration_plan.md`.
- Priority conclusion after re-checking `docs/project_focus_and_direction.md`:
  - WeChat is strategically high priority because the direction doc explicitly calls for exploring WeChat or another easier family-facing entry
  - but immediate coding priority still starts with Telegram/web Milestone 1, because WeChat should reuse the same shared binding-state and auth-outcome layer
  - recommended sequence:
    - immediate next: Telegram/web Milestone 1
    - next major spike: WeChat transport integration

## Session Update (2026-03-23, Milestone 1 implementation)
- Implemented a shared derived identity-access helper in `app/core/auth_service.py`:
  - `IdentityAccessState`
  - `AuthService.describe_identity_access(provider, provider_user_id)`
- Updated Telegram entry flow in `app/interfaces/telegram.py` to use the shared access-state helper for:
  - `/start login_*` handoff approval gating
  - guest vs bound welcome/help behavior
- Improved onboarding/handoff wording in `app/core/i18n.py` so unbound Telegram users get clearer next steps.
- Updated `web/src/app/login/page.tsx` to:
  - position Telegram as the primary sign-in path
  - keep API key login framed as admin/recovery fallback
  - show clearer guidance when Telegram sign-in is rejected because the account is not linked
- Updated targeted tests in `tests/test_telegram_login_handoff.py`.
- Verification completed:
  - `uv run pytest tests/test_telegram_bind_flow.py tests/test_telegram_login_handoff.py tests/test_auth_telegram_handoff.py tests/test_auth_core.py`
  - all 13 tests passed
  - `cd web && npm run lint -- src/app/login/page.tsx` passed with one remaining pre-existing warning about raw `<img>` usage

## Session Update (2026-03-23, Milestone 2 partial)
- Added shared structured auth/bind outcome helpers in `app/core/auth_service.py`:
  - `BindAttemptOutcome`
  - `LoginHandoffStatus`
  - `AuthService.describe_bind_attempt(...)`
- `AuthService.get_telegram_login_status(...)` now returns structured `detail` and `next_step` fields in addition to `status` / `exchange_token`.
- `app/api/auth.py` response model was extended to expose those fields.
- `app/interfaces/telegram.py` and `app/core/worker.py` now reuse the same bind-outcome mapping instead of hand-writing provider/user conflict message selection.
- `web/src/app/login/page.tsx` now consumes backend-provided status detail for rejected/expired Telegram handoff states.
- Added focused tests for:
  - structured Telegram handoff status payloads
  - bind-outcome message-key mapping
- Verification completed:
  - `uv run pytest tests/test_telegram_bind_flow.py tests/test_telegram_login_handoff.py tests/test_auth_telegram_handoff.py tests/test_auth_core.py`
  - all 15 tests passed

## Session Update (2026-03-23, bootstrap reprioritization)
- Added `docs/architecture/bootstrap_owner_flow.md`.
- Key product decision:
  - a fresh Nexus deployment should not start with normal login
  - it should start with a restricted bootstrap / owner-claim flow
  - the owner should bind Telegram during bootstrap and become the initial admin
- Priority order was updated accordingly:
  - first: bootstrap owner flow
  - second: post-bootstrap Telegram/web auth polish
  - third: WeChat transport spike

## Session Update (2026-03-23, docs-first adjustment)
- After further discussion, the team decided a full bootstrap/setup UI is likely premature for the current stage.
- Updated direction:
  - document the first-run flow clearly in `README.md`
  - keep startup simple: configure `.env`, launch, read initial admin credentials from logs, then optionally configure Telegram
  - postpone bootstrap UI/productization until real setup pain is better validated
- Supporting updates made:
  - `README.md` now describes the practical first launch path
  - `.env.example` now includes `TELEGRAM_BOT_USERNAME` and `JWT_SECRET`
  - `docker-compose.yml` now passes `TELEGRAM_BOT_USERNAME` into `nexus-app`

## Session Update (2026-03-23, hook workflow)
- Adjusted `scripts/check.sh`, which is invoked by `.git/hooks/pre-commit`, to operate on staged files instead of the whole repository.
- New hook behavior:
  - Python syntax check runs only for staged Python files under `app/`, `tests/`, and `scripts/`
  - Ruff check/format runs only on those staged Python files and re-stages any autofixes
  - ESLint runs for staged `web/` JS/TS files; changes to `web/package.json`, `web/package-lock.json`, `web/eslint.config.mjs`, or `web/tsconfig.json` trigger a full web lint run
  - pytest runs only on directly changed test files plus inferred related tests matching changed source-file stems
  - shared test/config changes such as `tests/conftest.py`, `pyproject.toml`, and `requirements-dev.txt` still trigger a full pytest run
  - staged `web/` changes still trigger the frontend build path
- Verification completed:
  - `bash -n scripts/check.sh` passed
  - `bash scripts/check.sh` passed in the current workspace state and exited early with no staged files
  - `cd web && npm run lint -- src/lib/auth.ts` reached ESLint successfully and reported an existing rule violation
- Existing issue surfaced by the new web lint:
  - `web/src/lib/auth.ts:22` uses `any` and currently fails `@typescript-eslint/no-explicit-any`
- Decision:
  - keep `scripts/dev_check.sh` unchanged as the full-repository validation path
  - use `scripts/check.sh` as the faster pre-commit gate

## Session Update (2026-03-23, admin wirelog auth fix)
- Fixed the admin audit page wirelog toggle to use bearer auth consistently with the rest of the JWT-backed admin UI.
- Root cause:
  - `web/src/app/audit/page.tsx` passed the signed-in JWT into `WireLogToggle`
  - `web/src/components/WireLogToggle.tsx` still sent that value as `X-API-Key`
  - backend auth then rejected it as `Invalid API Key`
- Changes made:
  - `WireLogToggle` now accepts a `token` prop instead of `apiKey`
  - both `GET /admin/config` and `POST /admin/config` now send `Authorization: Bearer <token>`
  - unauthorized copy now tells the admin to sign in again instead of checking an API key
- Verification completed:
  - `cd web && npm run lint -- src/components/WireLogToggle.tsx src/app/audit/page.tsx` passed

## Session Update (2026-03-23, admin web bearer cleanup)
- Searched the admin web surface for similar legacy `X-API-Key` usage after the wirelog bug.
- Cleaned up the remaining JWT-backed admin pages/components:
  - `web/src/app/cortex/page.tsx`
  - `web/src/app/users/page.tsx`
  - `web/src/app/users/[user_id]/page.tsx`
  - `web/src/app/integrations/page.tsx`
  - `web/src/app/integrations/PluginForm.tsx`
  - `web/src/app/integrations/EditPluginButton.tsx`
  - `web/src/app/integrations/ViewSkillButton.tsx`
- Main changes:
  - server-rendered admin pages now use `getServerAuthContext()` plus bearer headers instead of reading the JWT and then forwarding `payload.api_key`
  - client admin components now take `token` props instead of `apiKey`
  - plugin catalog/schema/skill fetches now send `Authorization: Bearer <token>`
- Verification completed:
  - `rg -n 'X-API-Key' web/src -S` found no remaining matches
  - `git diff --check` passed for all edited admin files
- Remaining verification gap:
  - targeted admin lint still fails due to pre-existing issues in these files (`any`, unused imports, hook dependency warnings, unescaped apostrophes), not because of the bearer-auth cleanup itself

## Session Update (2026-03-24, P0 recovery and audit detail)
- Improved recovery-oriented user messaging for key post-bind failure categories:
  - `permission_denied`
  - `invalid_input`
  - `unsafe_state`
- `WorkerDispatcher.build_report_message(...)` now tailors the suggested next step based on classification instead of always using one generic fallback.
- Added structured audit events for the auth and denial lifecycle:
  - `auth.bind_token_created`
  - `auth.binding_succeeded`
  - `auth.binding_conflict`
  - `auth.binding_failed`
  - `auth.binding_revoked`
  - `auth.telegram_login_started`
  - `auth.telegram_login_approved`
  - `auth.telegram_login_rejected`
  - `auth.telegram_login_completed`
  - `policy.action_denied`
- Telegram bind/login failure paths and auth API completion failure now emit audit events as part of normal execution.
- Verification completed:
  - `uv run pytest tests/test_auth_telegram_handoff.py tests/test_telegram_bind_flow.py tests/unit/test_worker_dispatcher.py tests/unit/test_audit.py`
  - `59 passed`

## Session Update (2026-03-25, local model benchmark subsystem planning)
- Added `docs/architecture/local_model_benchmark_subsystem.md`.
- Intent of the new doc:
  - define a durable benchmark subfunction for evaluating local models inside the Nexus LangGraph architecture
  - make benchmark runs configuration-driven and repeatable
  - preserve raw run artifacts and standardized summaries for future comparison
- Key design decisions captured in the doc:
  - the benchmark must be agent-first, not chat-first
  - the official benchmark path should prefer a LangGraph-native execution path with deterministic fixture tools
  - scenario definitions, score formula, and runner behavior should each be versioned
  - benchmark results should be archived under a dedicated `benchmark_results/` tree instead of relying only on generic runtime trace storage
  - new candidate models should be added by manifest/config change rather than prompt rewrites or script edits
- Recommended phase order:
  - Phase 1: versioned scenarios + fixture tools + runner + JSON archive output
  - Phase 2: deeper LangGraph-path reuse and benchmark-specific trace enrichment
  - Phase 3: comparison/reporting UX
- Verification:
  - reviewed current benchmark and model-related foundations:
    - `scripts/benchmark_v2.py`
    - `app/core/agent.py`
    - `app/core/llm_utils.py`
    - `app/models/llm_trace.py`
    - `app/core/trace_logger.py`
  - confirmed the new work in this session is documentation/context only; no runtime code paths were changed

## Session Update (2026-03-25, admin user channel binding visibility)
- Refined the admin users surface so channel binding state is visible without opening every user detail page.
- Initial attempt overloaded `GET /users/` with aggregated channel state, which later caused the users page to regress into an empty list when that path failed.
- The stable follow-up shape now keeps `GET /users/` unchanged and adds a dedicated admin summary endpoint:
  - `GET /users/channel-statuses`
  - returns `telegram_bound`, `telegram_username`, `wechat_bound`, and `wechat_polling_active`
- `web/src/app/users/page.tsx` now renders direct Telegram and WeChat status columns in the users table from that dedicated status endpoint.
- `web/src/app/users/[user_id]/page.tsx` now shows explicit Telegram and WeChat bound/not-bound state in the identity summary card.
- `web/src/app/users/[user_id]/WeChatBindingCard.tsx` now:
  - avoids showing the default `Bind WeChat` button while current status is loading
  - hides the default bind CTA once WeChat is already connected
  - keeps reconnect available as an explicit secondary action in the connected state
- Product/UI decision from this pass:
  - do not add WeChat unbind yet
  - the current UX should distinguish clearly between unbound and already-connected users
  - a future pass can add true unbind/runtime teardown if the product needs it

## Session Update (2026-03-28, skill routing anchor recall planning)
- Confirmed that the current browser query failure is no longer caused by MCP transport:
  - Playwright MCP is now connected and browser tools register successfully
  - the observed miss happens because `route_skills()` does not select `web_browsing` for natural-language research/search requests
- Read the current routing foundations in:
  - `app/core/tool_router.py`
  - `app/core/skill_loader.py`
  - `docs/architecture/semantic_routing.md`
- Added a new architecture note:
  - `docs/architecture/skill_routing_anchor_recall_with_local_vector_db.md`
- Recommendation from this session:
  - keep the current layered router
  - upgrade skill recall from one-vector-per-skill to multi-anchor-per-skill
  - add `routing_examples` / synthetic queries per skill
  - persist those anchors in the existing local Postgres + pgvector stack
  - aggregate recalled anchor hits back to skills before final tool binding
- Why this direction was chosen:
  - it directly addresses natural-language misses like “最新 AI 论文” not recalling `web_browsing`
  - it fits the current repo better than introducing a second vector system
  - it creates durable, inspectable routing knowledge instead of transient in-memory embeddings only
- Recommended next implementation order:
  - extend skill metadata with `routing_examples`
  - add a pgvector-backed `skill_routing_anchor` model/table
  - update `route_skills()` to use anchor aggregation
  - start with `web_browsing` as the first high-value skill
- Verification:
  - documentation and project-context update only
  - no runtime code paths changed in this session

## Session Update (2026-03-28, routing examples loaded without prompt bloat)
- Implemented the first practical step of the routing-anchor plan without changing the prompt budget.
- Changes made:
  - added curated `routing_examples` to the highest-value current skills:
    - `skills/web_browsing.md`
    - `skills/homeassistant.md`
    - `skills/python_sandbox.md`
    - `skills/cron_scheduler.md`
    - `skills/memory_management.md`
    - `skills/system_management.md`
  - upgraded `app/core/skill_loader.py` to parse frontmatter with real YAML support instead of the old line-splitting parser
  - added frontmatter sanitization so routing-only metadata such as `routing_examples` is removed from the prompt-facing `full_content`
  - updated `app/core/tool_router.py` so `register_skills()` includes `routing_examples` in the skill embedding text used for semantic routing
- Important implementation boundary:
  - these examples now improve the startup-built skill routing index
  - they do not enter the LLM system prompt
  - they are not yet persisted into a pgvector-backed `skill_routing_anchor` table
- Why this step was chosen:
  - it delivers an immediate recall improvement for browser/home-assistant/sandbox-like requests
  - it preserves context budget by keeping routing samples out of active skill prompt injection
  - it prepares the metadata shape needed for the next pgvector persistence step
- Verification completed:
  - `uv run ruff check app/core/skill_loader.py app/core/tool_router.py tests/test_skill_loader.py`
  - `uv run pytest tests/test_skill_loader.py tests/unit/test_skill_routing.py`
  - result: `14 passed`

## Session Update (2026-03-28, routing-example generation API and uninstall-safe refresh)
- Implemented the next backend step for routing-example generation during MCP/skill registration.
- Changes made:
  - added a dedicated routing-example generation prompt and method in `app/core/skill_generator.py`
  - added `POST /api/skills/generate-routing-examples` in `app/api/skills.py`
  - this path is intended for admin registration flows and returns candidate user-language routing examples as JSON
- Also tightened runtime consistency around skill installation/removal:
  - added `SkillLoader.refresh_runtime_skill_registry()` to rebuild the in-process skill routing index from current skill files
  - `/api/skills` save/delete now refresh runtime routing immediately
  - Telegram `/skill install` and `/skill uninstall` now refresh runtime routing after successful changes
  - `DELETE /plugins/{plugin_id}` now resolves bundled skills from `plugin_catalog.json`, removes unreferenced skill files, and refreshes runtime routing so removed skills do not keep matching in memory
- Important boundary:
  - this now prevents prompt-bloat and most in-memory ghost-skill matches after uninstall
  - true cross-store atomicity with future pgvector anchors still needs the next persistence step, where skill file changes and `skill_routing_anchor` row changes should be committed together
- Verification completed:
  - `uv run ruff check app/api/skills.py app/api/plugins.py app/core/skill_generator.py app/core/skill_loader.py app/interfaces/telegram.py tests/test_skill_generator.py tests/unit/test_plugin_skill_cleanup.py`
  - `uv run pytest tests/test_skill_loader.py tests/unit/test_skill_routing.py tests/test_skill_generator.py tests/unit/test_plugin_skill_cleanup.py`
  - result: `17 passed`

## Session Update (2026-03-28, main and skill-generation LLM settings)
- Added an explicit LLM configuration surface for both runtime chat and skill-generation workflows.
- Backend changes:
  - `app/core/config.py` now includes `SKILL_GEN_BASE_URL`
  - `app/core/llm_utils.py` now accepts explicit override parameters for `api_key`, `base_url`, and `model_name`
  - `app/core/skill_generator.py` now prefers a dedicated skill-generation endpoint when configured, and otherwise falls back field-by-field to the main LLM config
  - `app/api/admin.py` now exposes:
    - `GET /admin/llm-config`
    - `POST /admin/llm-config`
    - covering `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `SKILL_GEN_BASE_URL`, `SKILL_GEN_API_KEY`, and `SKILL_GEN_MODEL`
- Frontend changes:
  - added `web/src/app/llm/page.tsx`
  - added `web/src/app/llm/LLMSettingsForm.tsx`
  - added `web/src/app/actions/llm.ts`
  - added an `LLM` entry to the main admin sidebar in `web/src/components/Layout.tsx`
- Config/runtime changes:
  - `.env.example` now documents the optional dedicated skill-generation LLM variables
  - `docker-compose.yml` now passes those variables into `nexus-app`
- Product behavior:
  - main agent LLM can now be edited from the admin UI
  - skill/routing-example generation can temporarily share the same main LLM
  - if a dedicated skill-generation model/API is later configured, it can diverge cleanly without changing code paths
- Verification completed:
  - `uv run ruff check app/api/admin.py app/core/config.py app/core/llm_utils.py app/core/skill_generator.py`
  - `uv run pytest tests/test_skill_generator.py tests/test_skill_loader.py tests/unit/test_skill_routing.py tests/unit/test_plugin_skill_cleanup.py`
  - `cd web && npm run lint -- src/app/llm/page.tsx src/app/llm/LLMSettingsForm.tsx src/components/Layout.tsx src/lib/locale.ts src/app/actions/llm.ts`
  - backend checks passed
  - frontend lint passed with one pre-existing warning in `web/src/components/Layout.tsx` for raw `<img>` usage

## Session Update (2026-03-28, pgvector-backed skill routing anchors)
- Implemented durable skill routing storage on top of the existing Postgres + pgvector stack.
- Changes made:
  - added `app/models/skill_routing_anchor.py`
  - registered the new model in `app/models/__init__.py`
  - updated `app/core/db.py` to import `app.models`, ensuring `SQLModel.metadata.create_all()` sees the routing-anchor table
  - added `app/core/skill_routing_store.py`
- Runtime behavior changes:
  - `SkillRoutingStore.build_anchor_payloads(...)` now expands each skill into anchor rows for:
    - description
    - intent keywords
    - routing examples
  - `SemanticToolRouter.register_skills()` now syncs all current skills into `skill_routing_anchor`
  - skill sync also prunes anchors for removed skills, preventing database-side ghost matches
  - `SemanticToolRouter.route_skills()` now prefers pgvector anchor recall and skill-level aggregation
  - if DB lookup fails for any reason, it falls back to the previous in-memory skill embedding index
- Product impact:
  - accepted `routing_examples` are no longer transient startup-only hints
  - they are now durable and available after restart
  - skill uninstall/delete now has a path to remove both the file-backed skill and its durable recall anchors on the next refresh
- Verification completed:
  - `uv run ruff check app/models/skill_routing_anchor.py app/models/__init__.py app/core/db.py app/core/skill_routing_store.py app/core/tool_router.py tests/unit/test_skill_routing_store.py`
  - `uv run pytest tests/unit/test_skill_routing.py tests/unit/test_skill_routing_store.py tests/test_skill_loader.py tests/test_skill_generator.py tests/unit/test_plugin_skill_cleanup.py`
  - result: `19 passed`

## Session Update (2026-03-28, alembic migration and duplicate-safe skill anchors)
- Formalized the new `skill_routing_anchor` table in Alembic.
- Added migration:
  - `alembic/versions/b9f8e7d6c5a4_add_skill_routing_anchor.py`
- Important migration behavior:
  - creates `skill_routing_anchor` if missing
  - tolerates environments where the table may already have been created by `SQLModel.metadata.create_all()`
  - deduplicates pre-existing rows before adding the unique constraint
  - adds a unique constraint on `(skill_name, anchor_type, text)` so duplicate examples cannot accumulate
  - adds the expected lookup indexes
- Also tightened runtime sync behavior:
  - `SkillRoutingStore.sync_skills()` now compares current file-derived anchors with DB anchors per skill
  - if a skill's anchors have not changed, it skips re-embedding and re-importing them
  - if a skill changed, only that skill's anchors are replaced
  - if a skill was removed, its anchors are pruned
- Verification completed:
  - `uv run ruff check app/models/skill_routing_anchor.py app/core/skill_routing_store.py alembic/versions/b9f8e7d6c5a4_add_skill_routing_anchor.py`
  - `uv run pytest tests/unit/test_skill_routing_store.py tests/unit/test_skill_routing.py tests/test_skill_loader.py tests/test_skill_generator.py tests/unit/test_plugin_skill_cleanup.py`
  - `.venv/bin/alembic heads`
  - current Alembic head: `b9f8e7d6c5a4`
- Verification completed:
  - `uv run ruff check app/api/users.py`
  - `cd web && npm run lint -- 'src/app/users/page.tsx' 'src/app/users/[user_id]/page.tsx' 'src/app/users/[user_id]/WeChatBindingCard.tsx'`

## Session Update (2026-03-25, admin web language switching)
- Added a first-pass frontend locale layer for the admin web UI.
- New files:
  - `web/src/lib/locale.ts`
  - `web/src/app/actions/preferences.ts`
  - `web/src/app/language/page.tsx`
  - `web/src/app/language/LanguageSettingsForm.tsx`
- Updated shell integration:
  - `web/src/app/layout.tsx` now resolves locale from a `nexus_locale` cookie and passes localized labels into the shared layout
  - `web/src/components/Layout.tsx` now includes a `Language` sidebar entry and localizes primary navigation/shell labels
  - `web/src/app/users/page.tsx` now uses the locale dictionary for users-page copy and table labels
- Product decision for this first pass:
  - keep locale switching cookie-backed and page-level instead of introducing route-prefixed locales
  - cover the shell and users page first, then expand page-by-page later as needed
- Verification completed:
  - `uv run ruff check app/api/users.py`
  - `cd web && npm run lint -- 'src/app/layout.tsx' 'src/components/Layout.tsx' 'src/lib/locale.ts' 'src/app/language/page.tsx' 'src/app/language/LanguageSettingsForm.tsx' 'src/app/actions/preferences.ts' 'src/app/users/page.tsx'`
  - lint result had one pre-existing `Layout.tsx` image optimization warning and no new errors

## Session Update (2026-03-25, local model benchmark MVP)
- Implemented the first runnable benchmark MVP as a sidecar subfunction.
- New code paths:
  - `app/benchmarks/models.py`
  - `app/benchmarks/evaluators.py`
  - `app/benchmarks/scoring.py`
  - `app/benchmarks/runner.py`
  - `app/benchmarks/fixtures/tools.py`
  - `app/benchmarks/scenarios/suite_v1/*.json`
  - `scripts/run_local_model_benchmark.py`
  - `docs/local_model_benchmark_usage.md`
- Current benchmark MVP focus:
  - tool-selection correctness
  - grounded final response quality
  - error rate / retry burden
- Current implementation shape:
  - deterministic fixture tools instead of live external systems
  - versioned benchmark suite with 5 fixed tasks
  - per-attempt JSON archive output
  - per-model summary JSON output
  - Markdown comparison table output
- Important design choice:
  - the current runner is a lightweight benchmark loop using tool binding plus fixture execution
  - it is intentionally not yet a full reuse of the production LangGraph graph
  - this keeps Phase 1 simple and runnable while preserving a clear path for deeper LangGraph fidelity later
- Verification completed:
  - `uv run pytest tests/unit/test_local_model_benchmark.py`
  - `uv run ruff check app/benchmarks scripts/run_local_model_benchmark.py tests/unit/test_local_model_benchmark.py`
  - `git diff --check -- app/benchmarks scripts/run_local_model_benchmark.py docs/local_model_benchmark_usage.md tests/unit/test_local_model_benchmark.py docs/architecture/local_model_benchmark_subsystem.md .project-context/docs/task/active/index.md .project-context/docs/task/active/summary.md`
- Observed environment note:
  - direct CLI help works through `./.venv/bin/python scripts/run_local_model_benchmark.py --help`
  - `uv run python ...` hit a local sandbox cache-permission issue, so the documented invocation should prefer `python3` or the repo virtualenv interpreter

## Session Update (2026-03-25, benchmark fairness for local Ollama)
- Tightened the benchmark runner to match the intended local benchmarking policy:
  - benchmark runs are local-direct, not Docker-based
  - models are evaluated serially, one at a time
  - Ollama-backed runs warm the target model before measured attempts
  - runner attempts to unload currently loaded Ollama models before switching
  - runner unloads the tested model after its batch completes
- Files updated:
  - `app/benchmarks/runner.py`
  - `docs/local_model_benchmark_usage.md`
  - `tests/unit/test_local_model_benchmark.py`
- Verification completed:
  - `uv run ruff check app/benchmarks scripts/run_local_model_benchmark.py tests/unit/test_local_model_benchmark.py`
  - `uv run pytest tests/unit/test_local_model_benchmark.py`
  - `git diff --check -- app/benchmarks scripts/run_local_model_benchmark.py docs/local_model_benchmark_usage.md tests/unit/test_local_model_benchmark.py`

## Priority Snapshot
- Highest priority now is not new UI or new auth architecture. It is validating the current docs-first first-run path in real usage:
  - configure `.env`
  - start the stack
  - obtain the initial admin credentials from backend logs
  - confirm web login works
  - optionally configure and bind Telegram afterwards
- After that, the next important product validation is the home daily-use loop:
  - message entry
  - identity/binding
  - safe Home Assistant control
  - audit visibility
- Immediate next engineering/product check after this session:
  - do a real-device pass on denied action wording and the new auth/policy audit events
  - verify the admin audit page is sufficient for diagnosing bind/login/denied flows during that pass
- WeChat remains strategically important, but should be treated as the next major spike only after the current setup path and post-setup usage are validated.
- Bootstrap/setup UI is explicitly deferred for now. Keep `docs/architecture/bootstrap_owner_flow.md` as future direction, not the immediate build target.

## Session Update (2026-03-24, WeChat phase 1 adapter)
- Implemented and committed a first-pass WeChat transport adapter as `da56d79` (`Add WeChat channel phase 1 adapter`).
- Added a new adapter at `app/interfaces/wechat.py` with:

## Session Update (2026-03-24, Playwright MCP transport repair)
- Repaired the Web Browser MCP connection path so Playwright tools can register into the agent:
  - `app/core/mcp_manager.py` now supports both legacy SSE and streamable HTTP (`/mcp`) transports
  - remote MCP requests now send a normalized `Host` header, which is required for the current Playwright MCP host allowlist when accessed via Docker service DNS
- Updated official Playwright plugin/catalog and runtime wiring:
  - `plugin_catalog.json` now points Web Browser to `http://mcp-playwright:3000/mcp`
  - `docker-compose.yml` now starts Playwright MCP with `--allowed-hosts mcp-playwright,localhost,127.0.0.1`
  - Playwright MCP was also switched from default `chrome` to `chromium` for ARM64 compatibility
- Realigned the web browsing skill card to the actual Playwright toolset:
  - replaced stale `browser_extract` / `browser_screenshot` references with `browser_snapshot` / `browser_take_screenshot`
- Verification completed for transport and registration:
  - direct `/mcp` initialize succeeded from `nexus-app`
  - Playwright MCP identified itself as `Playwright 0.0.68`
  - listed 22 browser tools
  - `MCPManager.reload()` successfully connected `Web Browser` and loaded those 22 tools
- Remaining runtime gap:
  - the current `node:20-slim` Playwright container is still missing browser system libraries even after `browser_install`
  - started switching the service image to `mcr.microsoft.com/playwright:v1.52.0-noble`, but the large image pull was still in progress at handoff time
- Recommended immediate next step:
  - finish the browser-ready image/runtime transition and rerun the minimal `https://s.weibo.com/top/summary` smoke test
  - iLink/OpenClaw header generation
  - QR login bootstrap and bot-token handling
  - `getupdates` long-poll loop
  - inbound text normalization into `UnifiedMessage`
  - outbound `sendmessage`
  - typing support via `getconfig` + `sendtyping`
  - structured audit events for WeChat login and message flow
- Wired WeChat startup into `app/main.py`, registered the outbound dispatcher path in `app/core/dispatcher.py`, and documented the needed env vars in `.env.example`.
- Tightened worker-side channel compatibility while doing the WeChat slice:
  - bind command detection now accepts plain `bind 123456` in addition to `/bind 123456`
  - provider identity extraction now explicitly handles WeChat metadata
  - bind-token audit events no longer misleadingly label the flow as Telegram-specific
- Verification completed:
  - `uv run pytest tests/test_wechat_interface.py tests/test_worker_channel_helpers.py tests/test_auth_telegram_handoff.py tests/test_telegram_bind_flow.py`
  - pre-commit staged checks also passed during commit, including related worker-dispatcher tests (`62 passed`)

## Immediate Next Step
- Do a real-device WeChat validation pass with `WECHAT_ENABLED=true` and confirm:
  - QR login starts and completes
  - inbound `getupdates` payloads match current assumptions
  - outbound replies deliver with the cached `context_token`
  - WeChat-side binding works naturally with `bind 123456`

## Session Update (2026-03-24, WeChat user-level QR binding)
- Product model was corrected after reviewing the vendor reference and user direction:
  - WeChat OpenClaw should be treated as a user-level ClawBot binding flow, not a global bot plus chat-side `/bind` flow.
  - Telegram keeps `/bind`; WeChat does not.
- Refactored `app/interfaces/wechat.py` from a single global runtime into a per-user session manager:
  - user-scoped bot tokens are stored in encrypted `Secret` rows under `WECHAT_BOT_TOKEN`
  - startup now loads and activates all bound user WeChat sessions
  - QR confirmation can immediately activate the bound user's poll loop
  - inbound WeChat messages now carry `user_id` so worker resolution can attach directly to the intended Nexus user
  - outbound replies route through the correct runtime session using a per-channel owner map
- Added admin APIs in `app/api/users.py` for WeChat binding:
  - `GET /users/{user_id}/wechat/status`
  - `POST /users/{user_id}/wechat/bind`
  - `GET /users/{user_id}/wechat/bind/{session_id}`
- Added admin UI on the user detail page:
  - `web/src/app/users/[user_id]/WeChatBindingCard.tsx`
  - QR modal with live polling, connection status, and reconnect flow
- Adjusted worker behavior:
  - explicit `msg.user_id` now wins during user resolution
  - bind interception is now Telegram-only, so WeChat messages no longer trigger chat-side bind handling
- Verification completed:
  - `uv run pytest tests/test_wechat_interface.py tests/test_worker_channel_helpers.py tests/test_auth_telegram_handoff.py tests/test_telegram_bind_flow.py`
  - `21 passed`
  - `cd web && npm run lint -- 'src/app/users/[user_id]/page.tsx' 'src/app/users/[user_id]/WeChatBindingCard.tsx'`

## Immediate Next Step
- Run a real-device admin-driven WeChat bind from the user detail page and confirm:
  - QR image renders correctly in the modal
  - QR scan returns a bot token and flips the session to `bound`
  - the correct user's runtime poller starts
  - the first real inbound message is attributed to the expected Nexus user

## Session Update (2026-03-24, security defaults hardened)
- Removed the insecure short static JWT fallback from the active auth path.
- `app/core/security.py` now provides:
  - `get_jwt_secret()` for dynamic JWT signing/verification
  - `ensure_runtime_security_settings()` to auto-generate and persist strong `JWT_SECRET` and `NEXUS_MASTER_KEY` values in `SystemSetting` on startup when missing or invalid
- `app/main.py` now runs the runtime security bootstrap during startup.
- `app/core/auth.py` and `app/api/auth.py` now read the JWT secret dynamically instead of capturing a short import-time default.
- Result:
  - the previous `InsecureKeyLengthWarning` from JWT should disappear after restart
  - the previous `NEXUS_MASTER_KEY is not set` warning should disappear after restart
  - user-scoped WeChat bot tokens can now be encrypted automatically without manual env setup
- Verification completed:
  - `uv run pytest tests/test_auth_core.py tests/unit/test_security.py tests/test_wechat_interface.py tests/test_auth_telegram_handoff.py`
  - `22 passed`
  - `uv run ruff check app/core/security.py app/core/auth.py app/api/auth.py app/main.py tests/test_auth_core.py tests/unit/test_security.py`

## Immediate Next Step
- Restart the backend once so the generated/persisted security settings are loaded cleanly into the running process, then confirm the previous JWT and master-key warnings are gone from logs.

## Session Update (2026-03-24, admin session-expiry recovery)
- Fixed the admin-web UX gap where client-side `401 Unauthorized` responses only showed a toast and left the user on the current page.
- Added `clearSession()` in `web/src/app/actions/auth.ts` so client code can clear the `httpOnly` `access_token` cookie without relying on a redirecting server action.
- Added shared client recovery logic in `web/src/lib/client-auth.ts`:
  - show a consistent `Session expired. Please log in again.` toast
  - clear the cookie on the server
  - navigate the browser back to `/login`
- Added a root-layout browser fetch interceptor in `web/src/components/AuthRedirectOnUnauthorized.tsx` and mounted it from `web/src/app/layout.tsx`.
  - For Bearer-authenticated browser requests, `401` is now handled globally instead of with scattered per-component checks.
- Standardized plugin-related server actions in `web/src/app/actions/plugins.ts` so both local missing-token cases and backend `401` responses clear the stale cookie and redirect from the server action itself.
- Removed the temporary per-component unauthorized branches from the integrations admin UI so the recovery path is centralized again.
- Verification completed:
  - `cd web && npm run lint -- src/components/AuthRedirectOnUnauthorized.tsx src/lib/client-auth.ts src/app/layout.tsx src/app/actions/auth.ts src/app/actions/plugins.ts src/app/integrations/PluginForm.tsx src/components/WireLogToggle.tsx src/app/integrations/EditPluginButton.tsx src/app/integrations/ViewSkillButton.tsx src/app/integrations/ReloadMCPButton.tsx`
  - `git diff --check -- web/src/components/AuthRedirectOnUnauthorized.tsx web/src/lib/client-auth.ts web/src/app/layout.tsx web/src/app/actions/auth.ts web/src/app/actions/plugins.ts web/src/app/integrations/PluginForm.tsx web/src/components/WireLogToggle.tsx web/src/app/integrations/EditPluginButton.tsx web/src/app/integrations/ViewSkillButton.tsx web/src/app/integrations/ReloadMCPButton.tsx`

## Immediate Next Step
- Manually reproduce the original revoked/expired-token path in the browser and confirm the integrations/admin UI now returns to `/login` after the session-expired toast instead of leaving the user in-place.

## Session Update (2026-03-24, sliding session refresh)
- Converted the admin web session model from fixed 24-hour expiry to sliding renewal.
- Backend auth changes:
  - `app/api/auth.py` now defines `ACCESS_TOKEN_EXPIRE_SECONDS`
  - token responses now include `expires_in`
  - new `POST /api/auth/refresh` reissues a JWT for an already-authenticated user
- Frontend session changes:
  - `web/src/app/actions/auth.ts` now exposes `refreshSession()` and centralizes cookie writes
  - `web/src/app/auth/telegram/complete-web/route.ts` now also uses backend-provided TTL metadata for cookie lifetime
  - `web/src/components/SessionKeepAlive.tsx` is mounted from `web/src/app/layout.tsx` and refreshes the session about one hour before expiry
- Result:
  - the base session length is still 24 hours
  - active admin use should no longer hard-expire at the original 24-hour mark
  - true expiry/revocation still falls back to the previously added global unauthorized redirect path
- Verification completed:
  - `uv run pytest tests/test_auth_refresh.py tests/test_auth_core.py`
  - `cd web && npm run lint -- src/components/SessionKeepAlive.tsx src/components/AuthRedirectOnUnauthorized.tsx src/lib/client-auth.ts src/app/layout.tsx src/app/actions/auth.ts src/app/auth/telegram/complete-web/route.ts`
  - `git diff --check -- app/api/auth.py web/src/app/actions/auth.ts web/src/app/layout.tsx web/src/components/SessionKeepAlive.tsx web/src/app/auth/telegram/complete-web/route.ts tests/test_auth_refresh.py`

## Immediate Next Step
- Manually validate in a browser that a long-lived admin tab refreshes session state before expiry and still cleanly falls back to `/login` if refresh is denied.

## Session Update (2026-03-25, MCP session isolation direction)
- Added `docs/architecture/mcp_session_isolation_and_browser_evolution.md`.
- This note captures the agreed browser/MCP evolution path:
  - near-term Playwright should remain a built-in, public, stateless, read-only browser plugin
  - authenticated browser use should not rely on shared MCP-side state
  - future login-bearing browser support should be implemented through Nexus-managed per-user MCP sessions
  - this should be generalized into a reusable MCP session isolation layer for future plugins, not treated as a Playwright-only special case
- Architectural recommendation from the note:
  - introduce a `tool_group` layer between plugin and tool for mixed-risk MCP servers such as Playwright
  - later introduce a dedicated `MCPSessionManager` distinct from `MCPManager`
  - use Playwright as the first adopter of the generic model, not the only one

## Immediate Next Step
- Convert the MCP session isolation note into a concrete implementation plan for:
  - Playwright tool-group policy
  - public stateless read-only browser phase
  - generic `MCPSessionManager` contract for future per-user MCP sessions

## Session Update (2026-03-25, chat session continuity design)
- Investigated why follow-up web chat turns like `继续呀` can lose prior context.
- Confirmed the root cause is architectural rather than model-side:
  - `app/main.py` defines `thread_id` on the request model for `/api/chat` and `/api/chat/stream`
  - but the web handlers do not resolve a `Session` from that id, do not load `SessionManager.get_history_with_summary(...)`, and do not set `session_id` in graph state
  - message-channel flows in `app/core/worker.py` already do the correct session restore/bootstrap path, so web and channel behavior have drifted apart
- Added `docs/architecture/session_context_continuation_plan.md`.
- Recommendation from the new design note:
  - treat `thread_id` as the canonical conversation id mapped to `Session.session_uuid`
  - return canonical `thread_id` values from chat responses
  - add a shared session bootstrap helper so web chat, streaming chat, voice, and message channels all reconstruct context the same way
  - ship a P0 fix first for `/api/chat` and `/api/chat/stream`, then extract the shared helper and add regression coverage for follow-up turns

## Immediate Next Step
- Implement the web chat session-continuation P0 fix:
  - reuse `SessionManager` history restoration in `/api/chat` and `/api/chat/stream`
  - return canonical `thread_id` to the client
  - add regression tests proving a second-turn `继续呀` request sees the earlier turn context

## Session Update (2026-03-25, chat session continuity implementation)
- Implemented the web chat continuity P0 fix.
- Added shared session bootstrap logic in `app/core/chat_session_bootstrap.py`:
  - resolves or creates a persistent session from `thread_id`
  - reconstructs the graph input from archived summary plus recent raw turns
  - persists the current user message before graph execution so later turns can recover both sides of the conversation
- Updated `app/main.py`:
  - `/api/chat` now restores session context and returns `thread_id` plus `created_new_thread`
  - `/api/chat/stream` now restores session context and emits an initial `session` SSE event with `thread_id`, `created_new_thread`, and `trace_id`
- Updated `app/core/session.py` with `resolve_session(...)` so callers can tell whether a new thread was created.
- Updated `app/core/worker.py` to reuse the same bootstrap helper, reducing drift between web and message-channel conversation assembly.
- Added regression coverage in `tests/test_api.py` for a two-turn web chat flow:
  - first turn sends `帮我搜索天气`
  - second turn sends `继续呀` with the returned `thread_id`
  - the second graph invocation now sees the earlier human turn and reuses the same session id
- Verification completed:
  - `uv run ruff check app/main.py app/core/chat_session_bootstrap.py app/core/session.py app/core/worker.py tests/test_api.py`
  - `uv run pytest tests/test_api.py -q`
  - result: `5 passed`

## Immediate Next Step
- Manually validate the real web client and any stream consumer against the new chat contract:
  - confirm the frontend stores and reuses returned `thread_id`
  - confirm streaming clients handle the initial `session` SSE event before token/tool events

## Session Update (2026-03-25, summary behavior documentation)
- Added `docs/architecture/session_context_summary_current_behavior.md`.
- This note records the current non-optimized behavior of the session summary subsystem:
  - `PREVIOUS CONTEXT SUMMARY` is injected only when the session already has stored `SessionSummary` rows
  - summary generation is LLM-based and is triggered by `maybe_compact(...)` once unarchived message count exceeds the current threshold
  - archived summary source material may include user, assistant, and tool messages
  - current restore and pruning limits are documented explicitly so future optimization work can compare against the baseline

## Immediate Next Step
- No immediate code change required for summary optimization; revisit later if continuity quality, token cost, or long-session scaling becomes a priority

## Session Update (2026-03-25, chat continuity diagnostics)
- Added explicit diagnostics for session restoration and thread reuse.
- `app/main.py` now logs:
  - incoming sync/stream chat request mode
  - requested `thread_id`
  - resolved `thread_id`
  - whether a new thread was created
  - trace id and short prompt/response previews
- `app/core/chat_session_bootstrap.py` now logs:
  - whether previous summary existed
  - how many raw human/assistant/tool messages were restored
- `app/core/session.py` now emits a warning when a requested `thread_id` does not resolve for the current user and a new session must be created.
- Verification completed:
  - `uv run ruff check app/main.py app/core/chat_session_bootstrap.py app/core/session.py`

## Immediate Next Step
- Reproduce the failing follow-up once and inspect the new `CHAT REQUEST`, `CHAT SESSION RESTORE`, and `CHAT SESSION MISS` log lines to confirm whether the caller is reusing the same `thread_id`

## Session Update (2026-03-28, continuity root-cause review and race fix)
- Re-reviewed the code path for missing web chat context after the `thread_id` work landed.
- Confirmed one real backend race condition in the existing implementation:
  - assistant replies and tool outputs were persisted via `asyncio.create_task(_persist_message(...))` in `app/core/agent.py`
  - this meant the HTTP response could return before the latest assistant/tool messages were committed
  - if the user immediately sent a follow-up, session restoration could miss the just-finished turn and present the next request as if little or no prior context existed
- Fixed this by making assistant and tool persistence synchronous within the graph step before control returns to the caller.
- Additional code-level finding:
  - there is still no in-repo web chat client using `/api/chat` or `/api/chat/stream`; any actual caller must therefore be external or not yet committed here
  - so a remaining production issue could still be caused by the caller not reusing `thread_id`, but that cannot be proven from repo code alone
- Verification completed:
  - `uv run ruff check app/core/agent.py app/main.py app/core/chat_session_bootstrap.py app/core/session.py app/core/worker.py tests/test_api.py`
  - `uv run pytest tests/test_api.py tests/test_agent.py -q`
  - result: `31 passed`

## Immediate Next Step
- Reproduce once with the new diagnostics and check whether the caller is:
  - reusing the same `thread_id`
  - hitting `CHAT SESSION MISS`
  - restoring zero or unexpectedly few raw messages even after the persistence race fix

## Session Update (2026-03-28, Docker mirror configuration)
- Updated Docker build mirror handling to favor collaboration-friendly switching.
- Changes made:
  - `Dockerfile` now keeps official upstream defaults for Python `pip` only, because that image does not run `apt`
  - `web/Dockerfile` now keeps official upstream defaults for Alpine `apk` and `npm`
  - `docker-compose.yml` and `docker-compose.test.yml` pass only the mirror variables each image actually consumes, with official fallbacks when `.env` does not override them
  - `.env.example` now documents both official defaults and commented mainland China examples
- Decision:
  - do not hard-code mainland mirrors into Dockerfiles
  - allow each collaborator to switch sources by editing only local `.env`
- Verification completed:
  - `docker compose -f docker-compose.yml config`
  - `docker compose -f docker-compose.test.yml config`
  - both compose files rendered successfully after the mirror configuration adjustment

## Immediate Next Step
- If needed, test one build with official defaults and one build with mainland overrides in `.env` to confirm the switching behavior end to end.

## Session Update (2026-03-28, dashboard and directory cleanup)
- Removed the legacy Streamlit dashboard implementation from the repository.
- Changes made:
  - deleted the old `dashboard/` tree
  - removed `streamlit` from `requirements.txt` and `pyproject.toml`
  - deleted dashboard-only and JWT debug/test leftovers:
    - `tests/test_dashboard_imports.py`
    - `test-jwt.js`
    - `test_token.txt`
    - `web/test_jose.js`
    - `web/token.txt`
  - deleted the unused empty repo directory `app/storage/`
  - clarified in code comments that `/app/storage/sandbox_data` refers to the repo-root `storage/sandbox_data` path inside the container
  - updated current-facing docs/guides to refer to the Next.js web admin UI rather than the removed Streamlit dashboard
- Decision:
  - keep `storage/` as the real sandbox output directory
  - treat `docs/task.md` dashboard references as historical notes for now rather than active runtime guidance
- Verification completed:
  - `uv run ruff check app/core/db.py app/core/mcp_middleware.py app/tools/sandbox.py`
  - `cd web && npm run lint -- src/middleware.ts`
  - `uv run pytest -q tests/test_imports.py`
  - `docker compose -f docker-compose.yml config`

## Session Update (2026-03-28, plugin skill source-url fallback)
- Fixed an admin integrations regression where "View Skill" could fail for installed plugins if the plugin row had no `manifest_id`.
- Root cause:
  - `app/api/plugins.py` install/delete logic already supported catalog fallback by `source_url`
  - but `GET /api/plugins/{id}/skill` and `GET /api/plugins/{id}/schema` still hard-required `manifest_id`
  - this made the frontend fail only for the view/schema path, even when the plugin itself was otherwise valid
- Implemented a shared catalog-entry helper and applied the same fallback logic to schema and skill lookup.
- Added focused tests covering `source_url` fallback for both endpoints.
- Verification completed:
  - `uv run pytest tests/unit/test_plugin_skill_cleanup.py tests/unit/test_plugin_skill_api.py`
  - `4 passed`
  - `uv run ruff check app/api/plugins.py tests/unit/test_plugin_skill_api.py tests/unit/test_plugin_skill_cleanup.py`
  - all checks passed

## Session Update (2026-03-28, integrations same-origin API fix)
- Continued debugging after the user reported the frontend still showed `Failed to connect to plugin registry.` on the Integrations page.
- Root cause:
  - browser-side integrations components were using `NEXT_PUBLIC_API_URL` with a fallback of `http://localhost:8000/api`
  - in `docker-compose.yml`, `web` also exported `NEXT_PUBLIC_API_URL=http://localhost:8000/api`
  - this only works when the browser is running on the same machine as the stack; remote/browser-accessed deployments will send requests to the viewer's own localhost instead of the server
- Added `web/src/lib/client-api.ts` with a same-origin-safe helper:
  - default browser API base is `/api`
  - `localhost` / `127.0.0.1` public env values are normalized back to `/api`
- Updated integrations browser-side components to use the helper:
  - `web/src/app/integrations/PluginForm.tsx`
  - `web/src/app/integrations/EditPluginButton.tsx`
  - `web/src/app/integrations/ViewSkillButton.tsx`
- Updated `docker-compose.yml` so `web` now exports `NEXT_PUBLIC_API_URL=/api`.
- Verification completed:
  - `cd web && npm run lint -- src/app/integrations/PluginForm.tsx src/app/integrations/ViewSkillButton.tsx src/app/integrations/EditPluginButton.tsx src/lib/client-api.ts`
  - exited successfully

## Session Update (2026-03-28, session workspace lifecycle review)
- Reviewed the newly added session-scoped sandbox / inspector / MCP artifact flow to answer lifecycle and isolation questions precisely.
- Confirmed workspace layout is `SANDBOX_DATA_DIR/users/<user_id>/sessions/<session_id>/`.
- Confirmed `python_sandbox` uses that directory as its working directory, and MCP large-result offloads are also written there.
- Confirmed inspector tools operate only inside the current session workspace and block path escape.
- Confirmed current lifecycle gap:
  - `SessionManager.clear_history()` deletes DB message history only
  - it does not remove session workspace files
  - there is no TTL sweeper, quota enforcement, or stale-workspace cleanup yet
- Practical consequence:
  - browser outputs are searchable with inspector only when middleware offloads them into workspace files
  - smaller inline browser/tool responses are not automatically materialized as files for grep/read
- Recommended next step:
  - add explicit workspace cleanup on session reset/delete
  - add periodic TTL cleanup for stale workspaces under `SANDBOX_DATA_DIR/users/*/sessions/*`
  - optionally add per-session or per-user size quotas

## Session Update (2026-03-28, session workspace cleanup implementation)
- Implemented workspace cleanup on session reset:
  - `SessionManager.clear_history()` now deletes session messages, session summaries, and the current session workspace on disk.
- Added reusable workspace lifecycle helpers in `app/tools/session_workspace.py`:
  - direct session workspace deletion
  - TTL-based stale workspace cleanup using latest descendant mtime
- Added a dry-run-by-default admin script:
  - `python scripts/admin/cleanup_session_workspaces.py`
  - use `--apply` to actually delete stale workspaces
  - default TTL is 168 hours
- Added focused tests verifying:
  - session reset removes workspace files and summaries
  - stale workspace cleanup removes only old directories
- Verification completed:
  - `uv run ruff check app/core/session.py app/tools/session_workspace.py scripts/admin/cleanup_session_workspaces.py tests/unit/test_session_workspace_cleanup.py`
  - `uv run pytest tests/unit/test_session_workspace_cleanup.py tests/unit/test_inspector_tools.py tests/unit/test_session_budget_compact.py`
  - `5 passed`

## Session Update (2026-03-28, Plan A stabilization verification)
- Completed the current Plan A stabilization slice for browser-heavy flows:
  - 429 slow backoff retry
  - token-aware large-output guidance
  - pre-send token-budget compact gate
  - read-only inspector tools
  - session-scoped workspace cleanup
- Fixed a remaining sandbox runtime issue so the embedded audit prelude now receives a concrete `SANDBOX_DATA_DIR` value safely.
- Verified the combined Plan A surface with focused tests covering:
  - rate-limit retry
  - token budget guidance
  - token-aware compaction
  - inspector tool scoping
  - session workspace cleanup
  - sandbox workspace access
  - worker-aware tool filtering
- Verification completed:
  - `uv run ruff check app/core/llm_utils.py app/core/agent.py app/core/session.py app/tools/session_workspace.py app/tools/inspector_tools.py app/tools/sandbox.py app/core/tool_catalog.py app/tools/registry.py scripts/admin/cleanup_session_workspaces.py tests/unit/test_llm_utils_budget.py tests/unit/test_session_budget_compact.py tests/unit/test_inspector_tools.py tests/unit/test_session_workspace_cleanup.py tests/unit/test_sandbox_session_workspace.py tests/unit/test_tool_catalog.py`
  - `uv run pytest tests/unit/test_sandbox_session_workspace.py tests/unit/test_llm_utils_budget.py tests/unit/test_session_budget_compact.py tests/unit/test_inspector_tools.py tests/unit/test_session_workspace_cleanup.py tests/unit/test_tool_catalog.py`
  - `21 passed`

## Session Update (2026-03-28, built-in model capability catalog)
- Added a built-in model capability catalog for common API models not reliably covered by `tiktoken` model-name mappings.
- Runtime precedence is now:
  - explicit config values win
  - otherwise built-in catalog values apply
  - otherwise repository defaults apply
- Current catalog coverage includes:
  - Zhipu GLM
  - DeepSeek
  - Anthropic Claude
  - Google Gemini
  - Qwen / DashScope
- `build_token_budget(...)` and token-aware compact targeting now use effective model limits rather than only the static default values.
- Added `docs/architecture/model_capability_catalog.md` to record source families and operational notes.
- Verification completed:
  - `uv run ruff check app/core/model_capabilities.py app/core/llm_utils.py app/core/agent.py tests/unit/test_llm_utils_budget.py`
  - `uv run pytest tests/unit/test_llm_utils_budget.py`
  - `6 passed`
