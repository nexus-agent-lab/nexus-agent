# Phase 41 Decisions

## 2026-02-24: Architectural Decision - Split Backend/Frontend Phases

### Context
The Streamlit dashboard was built as a monolithic prototype that bypasses the FastAPI API layer, accessing PostgreSQL directly via SQLAlchemy (`from dashboard.utils import get_engine`). This pattern was suitable for early development but introduces security and scalability issues.

### Decision
Split the migration into three phases:
1. **P0 (Backend)**: Create RESTful FastAPI endpoints with proper authentication decorators
2. **P1 (Auth)**: Implement JWT-based session management in Next.js
3. **P2 (Frontend)**: Build Next.js pages that consume authenticated APIs

### Rationale
**Problems with Current Architecture:**
- No authentication enforcement on dashboard operations (Streamlit runs in trusted network)
- Tight coupling to database schema - breaks when schema changes
- Difficult to extend to multi-user web interface
- Cannot be exposed outside trusted networks safely
- Audit logs are incomplete (dashboard operations not tracked)

**Benefits of Split Approach:**
- **Security**: All data access goes through FastAPI layer with `@require_admin` and `@with_user` decorators
- **Audit Trail**: Every operation is logged with user attribution via AuditLog table
- **Scalability**: Stateless, RESTful architecture supports horizontal scaling
- **Future-proof**: Enables mobile apps, native clients, third-party integrations
- **Testability**: Backend APIs can be tested independently (Postman, curl)
- **Gradual Migration**: Keep Streamlit operational during transition

### Implementation Notes
- **P0 APIs must use decorators**: All new endpoints in `app/api/` must use `@require_admin` for admin operations and `@with_user(user_id)` for user-scoped access
- **JWT Payload**: `{user_id, username, role, api_key}` stored in httpOnly cookies
- **Feature Parity Constraint**: No new features - only migrate what exists in Streamlit dashboard
- **Streamlit Remains**: Keep Streamlit dashboard running during migration for fallback

### Trade-offs
- **Pro**: Clean separation of concerns, proper authentication, audit logging
- **Con**: More initial work (create APIs before UI), but pays off in long term
- **Con**: Duplicate validation logic (FastAPI + Next.js) - acceptable for migration phase

### Users API (User Management)
- Created `app/api/users.py` with standard CRUD endpoints for `User` and `UserIdentity` models.
- Used `get_current_user` combined with manual ID and role checks (e.g., `if current_user.id != user_id and current_user.role != "admin"`) to allow users to access their own data while restricting others, instead of relying purely on `require_admin`.
- Restricted `DELETE /users/{id}` to admins only (`Depends(require_admin)`).
- Prevented standard users from modifying their `role` (to prevent self-escalation to admin) and `policy` during a `PATCH` request.
- Handled `IntegrityError` to catch unique constraint violations for username, api_key, and identity bindings gracefully, returning 409 Conflict.
- Mapped the requested `IdentityBinding` model to the actual `UserIdentity` database model.

## MemSkillDesigner Integration
- Added `app/api/memskills.py` to handle memory skills and their Designer changelogs.
- `GET /memskills/stats` returns aggregate data previously calculated directly by pandas on the Cortex dashboard, eliminating the need for raw SQL on the frontend.
- `POST /memskills/{id}/evolve` explicitly maps to `MemSkillDesigner.evolve_skill(skill)`, whereas `POST /memskills/evolve` (no ID) maps to `MemSkillDesigner.run_evolution_cycle()` which evolves all underperforming skills.

## Memory Management API
- Implemented `app/api/memories.py` with `GET /memories` and `GET /memories/stats`.
- Did not expose the raw embedding vectors in the memory response to save bandwidth and improve security since the UI does not need to display them.
- Mounted the memories router in `app/main.py`.
- Enforced strict authorization: regular users can only fetch their own memories and stats, while admins can view any user's data.

## Telemetry Implementation
- Extracted telemetry logic out of the Streamlit dashboard and moved it into the core `app/api/telemetry.py` endpoints.
- Endpoints `GET /audit`, `GET /system/health`, `GET /system/redis`, and `GET /system/database` do not use a router prefix (they are root level or match exactly the required paths) to simplify API usage and fulfill requirements exactly.
- Used `AsyncSession` for executing `SELECT 1` for database health check.
- Re-used `MQService.get_redis()` method to connect to Redis without leaking multiple connection instances, checking lengths of inbox, outbox, and dlq queues.
- Handled errors gracefully in both Redis and Database checks to return error messages alongside status rather than raising unhandled exceptions.
- Protected all telemetry endpoints with `Depends(require_admin)` per requirements.

## 2026-02-25: Authentication Strategy - Cookie-based JWT

### Context
Implementing Next.js authentication to securely connect the Next.js frontend to the FastAPI backend.

### Decision
Use HTTP-only cookies to store the JWT access token instead of localStorage or other client-side storage mechanisms.

### Rationale
- **Security**: HTTP-only cookies are inaccessible to JavaScript, mitigating Cross-Site Scripting (XSS) attacks. This satisfies the strict requirement: "Do NOT store tokens in localStorage".
- **Server Actions & Middleware**: Next.js Server Actions and Middleware can natively read cookies, allowing seamless server-side rendering (SSR) and route protection without exposing the token to the client.
- **CSRF Protection**: By configuring cookies with `sameSite: "lax"`, we leverage browser-level protections against Cross-Site Request Forgery (CSRF), fulfilling the requirement: "Do NOT bypass CSRF protection".
- **State Management**: The middleware (`web/src/middleware.ts`) can intercept requests to protected routes (`/dashboard`, `/users`, etc.) and verify the JWT signature using the `jose` library before the page renders.

### Implementation Notes
- Created `web/src/app/actions/auth.ts` with `login` and `logout` Server Actions.
- Created `web/src/lib/auth.ts` to encapsulate JWT verification using `jose` (`jwtVerify`), ensuring we use the same `HS256` secret as the FastAPI backend.
- The `login` action submits the credentials (username and API key) as `application/x-www-form-urlencoded` to match the backend's `OAuth2PasswordRequestForm` requirement.
- Implemented `web/src/middleware.ts` to protect `/dashboard`, `/users`, `/cortex`, `/plugins`, and `/audit` routes, redirecting unauthenticated users to `/login`.

## P0 Backend API Endpoints Implementation
- Implemented `POST /users/{user_id}/bind-token` in `app/api/users.py` utilizing `AuthService.create_bind_token(user_id)`. Added strict RBAC checking to ensure users can only generate tokens for themselves, while admins can generate tokens for any user.
- Implemented `DELETE /users/{user_id}/identities/{identity_id}` in `app/api/users.py` utilizing `AuthService.unbind_identity(provider, provider_user_id)`. Included DB lookup to resolve `identity_id` to its `provider` and `provider_user_id` values, while validating ownership.
- Verified that `GET /memskills/{skill_id}` in `app/api/memskills.py` already exists and accurately returns `prompt_template` as part of `MemorySkillResponse`.
- Added missing `Depends(require_admin)` to `POST /admin/config`, `POST /admin/mcp/reload`, and `GET /admin/log` in `app/api/admin.py` to ensure proper security per constraints.
- Confirmed stability via `dev_check.sh` success.

### UI Component Choices
- **Timestamp Formatting**: Decided to use native `Intl.DateTimeFormat` (via `toLocaleTimeString`) for audit log timestamps to avoid adding `date-fns` as a dependency, keeping the frontend bundle lean and minimizing side effects.
- **Wire Log Toggle**: Implemented as a client component to provide immediate feedback, even though the backend doesn't currently expose a GET endpoint for the current state.

## 2026-02-26: Initial Admin Provisioning - Automatic Bootstrap on First Startup

### Context
New installations of Nexus Agent face a "chicken and egg" problem: users need an admin account to log into the Next.js dashboard, but no account exists initially.

### Decision
Implement automatic admin provisioning in `app/core/db.py` inside `init_db()` that creates the first admin user when the database is empty.

### Rationale
- **Zero-Friction Onboarding**: Users can start using the dashboard immediately without manual database scripts.
- **Secure by Default**: Uses `secrets.token_urlsafe(16)` to generate cryptographically secure API keys if none is provided.
- **Visible Feedback**: Displays credentials in a prominent ASCII box during startup logs, making it impossible to miss.
- **Environment Configuration**: Supports both automated deployments (via `INITIAL_ADMIN_API_KEY`) and manual setups (via generated keys).

### Implementation Notes
- Check user count using `select(func.count(User.id))` after `SQLModel.metadata.create_all`.
- Uses `AsyncSessionLocal` context manager to safely create and commit the admin user.
- Generates secure keys with `secrets.token_urlsafe(16)` (22 character, URL-safe base64).
- Prints a highly visible ASCII warning box with credentials via `logger.warning`.
- Default username from `INITIAL_ADMIN_USERNAME` env var (defaults to "admin").
- API key from `INITIAL_ADMIN_API_KEY` env var (optional, auto-generated if omitted).

### Trade-offs
- **Pro**: Eliminates manual DB setup steps for new users.
- **Pro**: Works seamlessly with Docker Compose first-boot scenarios.
- **Con**: Credentials visible in logs (acceptable for fresh installs, user can rotate later).
- **Con**: Only runs on truly empty databases (by design, prevents overwriting existing data).

## User Detail and Policy Editing (Task 10)
- **JSON Policy Editing**: Implemented using a standard `textarea` with client-side JSON validation before submission. This provides a balance between simplicity and functionality for administrative tasks.
- **Page Protection**: The User Detail page (`/users/[user_id]`) is restricted to users with the `admin` role, ensuring security for sensitive IAM operations.
- **Server Action**: Created `updateUser` in `web/src/app/actions/users.ts` to wrap the `PATCH /users/{id}` API endpoint. This action handles revalidation for both the users list and the specific user detail page.
- **Navigation**: Added a "Manage" action column to the Users list table to allow easy access to the detail page.
