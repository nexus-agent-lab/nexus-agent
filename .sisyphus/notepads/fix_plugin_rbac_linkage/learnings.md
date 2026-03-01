- The `check_tool_permission` logic was previously too restrictive, blocking users who met the role requirement but weren't in a specific `allow_domains` whitelist.
- Granting access immediately after the Vertical Gate (Role-based) check when no `allowed_groups` are present fixes this issue.
## Latency Logging Patterns
- Implemented LLM call latency tracking using `time.time()` in `app/core/agent.py`.
- Updated trace logs to include latency when `DEBUG_WIRE_LOG` is enabled.
- Verified syntax using `python3 -m py_compile`.
- Add backend API DELETE endpoint in FastAPI using SQLAlchemy session.delete and commit.
- Next.js Server Actions use `cookies` from `next/headers` to pass authentication.
- `revalidatePath` is imported from `next/cache` to refresh the UI after mutations.
Verified MemoryActions integration in Cortex UI.
