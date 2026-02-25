# Phase 41: Frontend Migration - Streamlit to Next.js + FastAPI

## Overview
Migrate Streamlit dashboard features to a modern Next.js frontend with FastAPI backend endpoints. This phase transitions Nexus Agent from Streamlit (which bypasses the API layer via direct SQLAlchemy access) to a proper web application with authenticated API access.

**Key Constraint:** Streamlit currently accesses the database directly via SQLAlchemy (`from utils import get_engine`), bypassing the FastAPI authentication layer. The migration must create proper FastAPI endpoints with `@require_admin` and `@with_user` decorators for all dashboard operations.

## Target Pages (Feature Parity)
1. **Dashboard** (`/dashboard`) - Main system status, quick actions, recent activity (from `Main.py`)
2. **IAM** (`/users`) - User management, roles, policies (from `1_IAM.py`, `6_Users.py`)
3. **Observability** (`/audit`) - Audit logs, telemetry, LLM debug (from `2_Observability.py`)
4. **Cortex** (`/cortex`) - Memory storage, skills management, evolution history (from `3_Cortex.py`)
5. **Network** (`/network`) - Tailscale status (from `4_Network.py`) - **P3**
6. **Integrations** (`/integrations`) - MCP servers, skill cards (from `5_Integrations.py`) - **P3**

---

## P0: Backend API Scaffolding
*Create FastAPI endpoints that Streamlit currently bypasses via direct DB access.*

### Users & IAM API (`app/api/users.py`)
- [x] Create `users.py` router file
- [x] `GET /users` - List all users with role and policy (admin only)
  - Use `@require_admin` decorator
  - Return: `[{id, username, role, api_key, policy, language, timezone}]`
- [x] `GET /users/{user_id}` - Get user details including identities (admin only)
  - Include `UserIdentity` relationships
  - Return: User object with `identities` array
- [x] `POST /users` - Create new user (admin only)
  - Fields: `username`, `role` (default: user)
  - Auto-generate `api_key`
  - Return: Created user with `api_key`
- [ ] `POST /users/{user_id}/bind-token` - Generate 6-digit binding token
  - Use existing `AuthService.create_bind_token()`
  - Return: `{token, expires_in}`
- [ ] `DELETE /users/{user_id}/identities/{identity_id}` - Unbind identity
  - Use existing `AuthService.unbind_identity()`
- [x] `PATCH /users/{user_id}` - Update user role and policy
  - Fields: `role`, `policy` (JSON)
  - Validate policy is valid JSON
  - Return: Updated user

### MemSkills API (`app/api/memskills.py`)
- [x] Create `memskills.py` router file
- [x] `GET /memskills` - List all memory skills
  - Query params: `status` (optional: active|canary|deprecated), `skill_type` (encoding|retrieval)
  - Return: Array with stats: `[{id, name, skill_type, version, status, positive_count, negative_count, is_base, created_at}]`
- [ ] `GET /memskills/{skill_id}` - Get skill details with prompt template
  - Return: Skill object including `prompt_template`
- [ ] `GET /memskills/stats` - Get skill statistics (for dashboard metrics)
  - Return: `{total, active_count, canary_count, deprecated_count, total_memories}`
- [x] `POST /memskills/changelog/approve` - Approve canary skill (admin only)
  - Body: `{changelog_id}`
  - Use existing `MemSkillDesigner.approve_changelog()`
- [x] `POST /memskills/changelog/reject` - Reject canary skill (admin only)
  - Body: `{changelog_id}`
  - Use existing `MemSkillDesigner.reject_changelog()`
- [x] `GET /memskills/changelog` - List skill evolution history
  - Query params: `limit` (default: 20), `status` (canary|approved|rejected)
  - Return: Array: `[{id, skill_name, reason, status, old_prompt, new_prompt, created_at, reviewed_at}]`

### Memory API (`app/api/memories.py`)
- [x] Create `memories.py` router file
- [x] `GET /memories` - List stored memories
  - Query params: `user_id` (optional), `limit` (default: 50), `memory_type` (profile|reflexion|knowledge)
  - Use `@with_user` decorator for user-scoped access
  - Return: `[{id, user_id, memory_type, content, skill_id, created_at}]`
- [x] `GET /memories/stats` - Get memory statistics
  - Return: `{total_count, type_counts, skill_linked_count}`

### Telemetry & Logs API (`app/api/telemetry.py`)
- [x] Create `telemetry.py` router file
- [x] `GET /audit` - List audit logs (existing in AuditLog table)
  - Query params: `limit` (default: 50), `status` (SUCCESS|FAILURE|DENIED), `user_id` (optional)
  - Use `@require_admin` for admin access, `@with_user` for user-scoped logs
  - Return: `[{id, trace_id, user_id, action, tool_name, tool_args, status, error_message, created_at, completed_at, duration_ms}]`
- [x] `GET /telemetry/health` - Get system health metrics (for Dashboard)
  - Check DB connection, LLM service status, Tailscale connectivity
  - Return: `{agent_core: "online", database: "connected"|"offline", llm_service: "ollama"|"cloud", tailscale: "active"|"inactive"}`
- [x] `POST /admin/config` - Update runtime config (existing endpoint, verify functionality)
  - Ensure `DEBUG_WIRE_LOG` toggle works for dashboard
- [ ] `POST /admin/mcp/reload` - Reload MCP servers (existing, verify)

---

## P1: Next.js Authentication Layer
*Implement login, session management, and route protection.*

### Authentication Setup
- [ ] Install dependencies:
  ```bash
  cd web && npm install next-auth@beta jose
  ```
- [ ] Create `web/src/app/api/auth/[...nextauth]/route.ts`
  - Configure credentials provider (username/password flow)
  - Store JWT in httpOnly cookies
  - JWT payload: `{user_id, username, role, api_key}`
- [ ] Create `web/src/lib/auth.ts` - Auth helper functions
  - `signIn()` - Call FastAPI `/auth/token` endpoint (create if needed)
  - `signOut()` - Clear session
  - `getSession()` - Get current user from JWT
  - `requireAuth()` - HOC for protected routes

### FastAPI Auth Token Endpoint
- [ ] Add `POST /auth/token` to `app/api/auth.py`
  - Body: `{username, api_key}` (or username/password)
  - Validate credentials against DB
  - Return: `{access_token, token_type: "bearer", user: {id, username, role}}`
- [ ] Add `GET /auth/me` endpoint
  - Validate JWT from Authorization header
  - Return: Current user details

### Middleware & Route Protection
- [ ] Create `web/src/middleware.ts` - Next.js middleware
  - Check JWT for protected routes (`/dashboard`, `/users`, `/audit`, `/cortex`)
  - Redirect to `/login` if not authenticated
  - Handle `/admin` routes (require role=admin)
- [ ] Create login page `web/src/app/login/page.tsx`
  - Form: username + API key (or password)
  - Store JWT on success, redirect to `/dashboard`
  - Show error on failed login

---

## P2: Next.js Pages (Core Dashboard)
*Build the main dashboard pages using Tailwind CSS and Server Components.*

### Shared Components (`web/src/components/`)
- [ ] Create `Layout.tsx` - Main app layout with sidebar navigation
  - Sidebar links: Dashboard, Users, Cortex, Audit, Network, Integrations
  - User profile dropdown (logout)
- [ ] Create `MetricCard.tsx` - Reusable metric display component
  - Props: `label`, `value`, `delta`, `color`
- [ ] Create `DataTable.tsx` - Reusable table component with search/filter
- [ ] Create `LoadingSkeleton.tsx` - Loading states

### Dashboard (`web/src/app/dashboard/page.tsx`)
*Feature parity: `dashboard/Main.py`*
- [ ] Create `/dashboard` page
- [ ] Display system status metrics (4 cards):
  - Agent Core: "Online" / "Offline"
  - Database: "Connected" / "Offline"
  - Network Status: "Active" / "Inactive"
  - Model Service: "Ollama" / "Cloud" + model name
- [ ] Quick actions section (buttons):
  - Clear cache (call `/admin/cache/clear` endpoint if exists)
  - Restart kernel (placeholder, requires background task)
  - Run diagnostics (call `/telemetry/health`)
- [ ] Recent activity table:
  - Fetch `/audit?limit=5`
  - Display columns: action, tool_name, status, created_at
  - Status color coding (green=SUCCESS, red=FAILURE, yellow=DENIED)

### Users & IAM (`web/src/app/users/page.tsx`)
*Feature parity: `dashboard/pages/1_IAM.py`, `dashboard/pages/6_Users.py`*
- [ ] Create `/users` page
- [ ] User list section:
  - Fetch `/users` (admin only)
  - Table: ID, username, role, API key, language, timezone
  - Expandable row details: show linked identities
- [ ] Create user form:
  - Fields: username, role (select: user|admin|guest)
  - Auto-generate API key
  - Submit to `POST /users`
- [ ] User detail view (`/users/[user_id]`):
  - Fetch `/users/{user_id}`
  - Show user info, linked identities list
  - "Generate Binding Token" button (call `POST /users/{user_id}/bind-token`)
  - Show token in modal with copy button
- [ ] Edit user role/policy form:
  - Role selector
  - Policy JSON editor (textarea with validation)
  - Submit to `PATCH /users/{user_id}`
- [ ] IAM policy matrix display:
  - Static table showing role-based permissions (admin/user/guest)
  - Reference `app/core/policy.py`

### Observability & Audit (`web/src/app/audit/page.tsx`)
*Feature parity: `dashboard/pages/2_Observability.py`*
- [ ] Create `/audit` page
- [ ] Tabs: "Real-time Audit Logs", "Trace Viewer", "LLM Debug"
- [ ] Audit Logs tab:
  - Fetch `/audit` with filters
  - Controls: limit slider, status filter (ALL/SUCCESS/FAILURE/DENIED)
  - Table: created_at, action, tool_name, status, tool_args (collapsible JSON)
  - Real-time refresh (use SWR polling)
- [ ] Trace Viewer tab:
  - Placeholder for future LangGraph trace visualization
  - Show message: "链路回放 (开发中)"
- [ ] LLM Debug tab:
  - Toggle switch for "Wire Log" (call `POST /admin/config` with `DEBUG_WIRE_LOG`)
  - Show instructions for viewing logs: `docker-compose logs -f --timestamps nexus-app`

### Cortex - Memory & Skills (`web/src/app/cortex/page.tsx`)
*Feature parity: `dashboard/pages/3_Cortex.py`*
- [ ] Create `/cortex` page
- [ ] Tabs: "Memory Storage", "Skills Management", "Evolution History"
- [ ] Memory Storage tab:
  - Fetch `/memories` and `/memories/stats`
  - Metrics row: Total memories, Memory types, Skills linked
  - Table: id, user_id, memory_type, content (truncated), skill_id, created_at
- [ ] Skills Management tab:
  - Fetch `/memskills`
  - Metrics: Total skills, Active, Canary, Deprecated
  - Bar chart: positive_count vs negative_count per skill
  - Skills list (expandable details):
    - Status emoji (green=active, yellow=canary, white=deprecated)
    - Health emoji based on negative_rate > 0.3
    - Show: version, skill_type, is_base, counts, negative_rate
    - Expand to show prompt_template (code block)
- [ ] Evolution History tab:
  - Fetch `/memskills/changelog`
  - Pending Canaries section (status=canary):
    - Warning banner with count
    - Each entry: skill_name, reason, old_prompt (truncated), new_prompt (truncated)
    - Approve/Reject buttons (call `/memskills/changelog/approve` or `/reject`)
  - Full history table: id, skill_name, status, reason, created_at, reviewed_at

---

## P3: Secondary Pages (Lower Priority)
*Pages with external dependencies or complex integrations.*

### Network Status (`web/src/app/network/page.tsx`)
*Feature parity: `dashboard/pages/4_Network.py`*
- [ ] Create `/network` page
- [ ] Tailscale status display:
  - Call backend to fetch `tailscale status --json` (requires admin endpoint)
  - Table: Hostname, IP, OS, Online status, Type (Local/Peer)
- [ ] Fallback to Tailscale Admin Console link if API unavailable
- [ ] Display connection info: "http://nexus-agent-server:8000"

### Integrations (`web/src/app/integrations/page.tsx`)
*Feature parity: `dashboard/pages/5_Integrations.py`*
- [ ] Create `/integrations` page
- [ ] Tabs: "MCP Servers", "Skill Cards", "Learning Audit"
- [ ] MCP Servers tab:
  - Read `mcp_server_config.json` via backend endpoint
  - Table: Name, Enabled, Skill File, Source, Command/URL, Required Role
  - "Reload Configuration" button
  - Add integration forms (local directory, Git clone)
- [ ] Skill Cards tab:
  - Fetch skills list via backend (existing `/skills/` endpoints)
  - Skill selector sidebar
  - AI generation form (based on MCP service)
  - Skill editor (Markdown textarea)
  - Save/Delete/Link to MCP buttons
- [ ] Learning Audit tab:
  - Learning mode toggle (manual/auto)
  - Fetch `/skill-learning/logs`
  - Pending review items with Approve/Reject buttons

---

## Dependencies & Prerequisites
- [ ] Phase 40 completion confirmed
- [ ] FastAPI backend running on port 8000
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Ollama service running (for LLM)
- [ ] Next.js project scaffolded (`/web` directory exists)

---

## Architecture Notes

### Why Split Backend/Frontend Phases?
The Streamlit dashboard was a monolithic prototype that bypassed the API layer, accessing PostgreSQL directly via SQLAlchemy. This architectural pattern worked for early development but introduces security and scalability issues:
- No authentication enforcement on dashboard operations
- Tight coupling to database schema (breaks with schema changes)
- Difficult to extend to multi-user web interface
- Can't be exposed outside trusted networks safely

The migration follows a clean separation:
1. **Backend (P0)**: Create RESTful endpoints with proper decorators (`@require_admin`, `@with_user`)
2. **Auth (P1)**: Implement JWT-based session management
3. **Frontend (P2)**: Build Next.js pages that consume authenticated APIs

This ensures all data access goes through the FastAPI layer, enabling:
- Role-based access control (RBAC)
- Audit logging for all operations
- Stateless, scalable architecture
- Future mobile/native app compatibility

### Key Decorators to Apply
- `@require_admin`: Routes that modify system state (create users, approve canaries)
- `@with_user(user_id)`: Routes that access user-specific data (memories, audit logs)
- `get_current_user`: Validate JWT from Authorization header

---

## Acceptance Criteria
- [ ] All P0 API endpoints created and tested (Postman/curl)
- [ ] Authentication flow works: login → JWT → protected routes
- [ ] `/dashboard` shows real system metrics
- [ ] `/users` allows creating/editing users and managing identities
- [ ] `/audit` displays audit logs with real-time updates
- [ ] `/cortex` shows memory and skills with canary approval workflow
- [ ] Streamlit dashboard still functional during migration (no breaking changes)
- [ ] All endpoints use proper decorators for access control
- [ ] No direct SQLAlchemy access from frontend

---

## Technical Debt to Track
1. **Wire Log endpoint**: `/admin/config` may need enhancement for LLM debug
2. **Tailscale API**: Requires container exec to fetch status (security concern)
3. **MCP Config**: Direct file I/O in Streamlit needs backend endpoint abstraction
4. **Skill Generation**: AI generation in Streamlit needs proper error handling in API
5. **Trace Visualization**: LangGraph trace viewer is placeholder only

---

## Rollback Plan
If migration fails:
- Keep Streamlit dashboard operational (`docker-compose up nexus-dashboard`)
- Document new API endpoints for future use
- Revert `app/main.py` changes if any
- Delete `web/` directory if no progress made

---

## Success Metrics
- [ ] Feature parity achieved for `/dashboard`, `/users`, `/audit`, `/cortex`
- [ ] All dashboard operations go through FastAPI (100% authenticated)
- [ ] Audit log shows all API requests with user attribution
- [ ] Next.js build succeeds without errors (`npm run build`)
- [ ] End-to-end user flow: login → view dashboard → create user → approve canary
