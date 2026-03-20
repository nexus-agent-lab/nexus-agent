# Summary

## Branch Intent
Continue P0-2 auth/login hardening after the Telegram↔web handoff MVP: remove frontend reliance on decoded JWT `api_key` extraction and move web/backend auth toward backend-verified Bearer JWT.

## Current State
- HA baseline work is documented in `docs/ha_p0_validation_checklist.md` and linked from `docs/task.md`.
- Auth design docs are in place: `docs/auth_channel_strategy.md` and `docs/auth_binding_state_machine.md`.
- Telegram bind UX was tightened earlier and committed (`59ed1f1`).
- Telegram↔web handoff MVP is implemented and committed:
  - `341e934` Document auth channel strategy
  - `b5abcd1` Add Telegram web login handoff backend
  - `4c116a9` Add Telegram handoff login UI
  - `18d5895` Use local uv checks and retire Streamlit entrypoint
- `scripts/dev_check.sh` now runs Ruff and pytest locally via `uv`; `docker-compose.yml` no longer starts the Streamlit dashboard service by default; README/agent docs now point to the web UI path.
- Latest verification succeeded: `./scripts/dev_check.sh` passed with frontend build success and `154 passed` tests.
- Exploration for the next auth-hardening slice has started:
  - Direct evidence already gathered shows backend auth still depends on `X-API-Key` in `app/core/auth.py`.
  - Many Next.js pages/actions still decode `access_token`, extract `payload.api_key`, and forward `X-API-Key`.
  - Background exploration task launched: `bg_a564cd0f` (session `ses_2f7558a39ffekIFEWaGG3WdZXS`) to map the smallest Bearer JWT migration slice.
- Infra follow-up completed for local Docker Compose routing:
  - `deploy/nginx/nexus.conf` now uses Docker DNS resolver `127.0.0.11` with variable-based `proxy_pass` targets for `nexus-app` and `web`, so nginx can re-resolve container IPs after service restarts without restarting nginx.
  - Verification completed with `docker compose config` and `docker run --rm ... nginx:1.27-alpine nginx -t`.
- GCC tree is partially incomplete for the active task: `.ai-governance/docs/task/active/task.md` and `.ai-governance/docs/task/active/verification.md` were missing during this session, so execution proceeded from the live user request and existing summary.

## Latest Commits
- `2026-03-20-0858-nginx-dns-reresolve`: Switch nginx proxy targets to Docker DNS re-resolution so Compose service restarts do not leave nginx pinned to stale container IPs.

## Known Risks
- Main unresolved security issue: web still decodes JWT client/server-side and forwards `payload.api_key` to the backend instead of relying on backend-verified Bearer JWT. Oracle previously flagged this as the next must-fix issue.
- Streamlit code still exists under `dashboard/`; only the active compose/runtime entrypoint was removed.
- `CLAUDE.md`, `.ai-governance/`, and other local/governance files remain uncommitted and were intentionally excluded from product commits.
- No implementation has started yet for the Bearer JWT migration; current state is exploration + planning only.
- Docker DNS re-resolution now depends on nginx querying `127.0.0.11`; if deployment topology later moves nginx outside the Compose network, this resolver must be adjusted.

## Next Action
Collect the result of `bg_a564cd0f`, then implement the smallest safe Bearer JWT hardening slice: add backend JWT auth support alongside existing API-key auth, centralize web auth headers around the raw `access_token`, and replace the highest-impact `payload.api_key` call sites first. If Compose routing regresses again, first re-check `deploy/nginx/nexus.conf` dynamic DNS behavior before changing service names or restart policies.
