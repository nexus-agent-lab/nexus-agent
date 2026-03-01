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
- The new logic in `auth_service.py:check_tool_permission` ensures that deny lists apply before anything else, admin users bypass other checks, and the domain sandbox applies only to unrestricted tools (where both `required_role` and `allowed_groups` are not present).
# Auth Service Audit Outcomes
- Verified `app/core/auth_service.py` meets the Sandbox Escape and Deny-First requirements.
- **Deny-First Precedence:** The Deny List evaluates before the Admin bypass. If a tool is in `policy["deny_tools"]`, access is denied immediately, effectively blocking Admins as well.
- **Rejection-Only Gates:** Role and Group checks act only as rejection gates (returning `False` if criteria are not met). They do not prematurely return `True`, ensuring that the authorization flow continues seamlessly.
- **Domain Sandbox:** Unrestricted tools (those without explicit `required_role` or `allowed_groups`) correctly fall into the Domain Sandbox evaluation as the final safety net before access is granted.
