# Commit: 2026-03-20-0858-nginx-dns-reresolve

## Intent
Make nginx in Docker Compose automatically recover backend routing after `nexus-app` restarts and receives a new container IP.

## Previous Context
The live user request was to adjust nginx so backend restarts no longer require an nginx restart. The current nginx config used static upstream hostnames, which nginx resolves once and can keep pinned to a stale container IP. The GCC tree was partially incomplete because `task.md` and `verification.md` were missing, so execution proceeded from the user request, existing summary, and the checked-in Compose/nginx files.

## Changes Made
- **File**: `deploy/nginx/nexus.conf`
  - Logic: Removed static `upstream` blocks, added Docker DNS resolver `127.0.0.11`, and switched `proxy_pass` to variable-based upstream targets so nginx re-resolves `nexus-app` and `web` periodically.
- **File**: `.ai-governance/docs/task/active/summary.md`
  - Logic: Recorded the infra routing fix, verification evidence, and the missing GCC files discovered during session startup.

## Decisions
- Use Docker's embedded DNS resolver instead of Compose restart-policy changes because the actual failure mode is stale name resolution inside nginx, not backend availability policy.
- Keep the fix inside nginx config only so the change is narrow, low-risk, and does not interfere with unrelated user modifications already present in the worktree.
- Preserve the `web` target in the same dynamic form for consistency, even though the immediate symptom reported was backend restart discovery.

## Verification
- [X] `docker compose config`
- [X] `docker run --rm -v "$PWD/deploy/nginx/nexus.conf:/etc/nginx/conf.d/default.conf:ro" nginx:1.27-alpine nginx -t`
- Evidence:
  - `docker compose config` succeeded for the current stack.
  - `nginx: the configuration file /etc/nginx/nginx.conf syntax is ok`
  - `nginx: configuration file /etc/nginx/nginx.conf test is successful`

## Risks / Next Steps
- This relies on nginx running inside the same Docker/Compose network where `127.0.0.11` is available; if nginx is later moved outside that network, resolver settings must be revisited.
- The running nginx container still needs one reload/restart to pick up the new config; after that, backend restarts should be discovered automatically.
