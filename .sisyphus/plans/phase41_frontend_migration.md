# Phase 41: Frontend Migration - Streamlit to Next.js + FastAPI

> **Date**: 2026-02-25
> **Vision**: Migrate Streamlit dashboard features to a modern Next.js frontend with FastAPI backend endpoints.

## Overview
Migrate Streamlit dashboard features to a modern Next.js frontend with FastAPI backend endpoints. This phase transitions Nexus Agent from Streamlit (which bypasses the API layer via direct SQLAlchemy access) to a proper web application with authenticated API access.

**Key Constraint:** Streamlit currently accesses the database directly via SQLAlchemy (`from utils import get_engine`), bypassing the FastAPI authentication layer. The migration must create proper FastAPI endpoints with `@require_admin` and `@with_user` decorators for all dashboard operations.

## Target Pages (Feature Parity)
1. **Dashboard** (`/dashboard`) - Main system status, quick actions, recent activity
2. **IAM** (`/users`) - User management, roles, policies
3. **Observability** (`/audit`) - Audit logs, telemetry, LLM debug
4. **Cortex** (`/cortex`) - Memory storage, skills management, evolution history
5. **Network** (`/network`) - Tailscale status (P3)
6. **Integrations** (`/integrations`) - MCP servers, skill cards (P3)

---

## P0: Backend API Scaffolding (COMPLETED)
- [x] Create `users.py` router file
- [x] `GET /users`, `GET /users/{user_id}`, `POST /users`, `PATCH /users/{user_id}`, `DELETE /users/{user_id}`
- [x] `POST /users/{user_id}/bind-token`, `DELETE /users/{user_id}/identities/{identity_id}`
- [x] Create `memskills.py` router file
- [x] `GET /memskills`, `GET /memskills/{id}`, `GET /memskills/stats`, `GET /memskills/changelogs`
- [x] `POST /memskills/changelogs/{id}/approve`, `POST /memskills/changelogs/{id}/reject`
- [x] Create `memories.py` router file
- [x] `GET /memories`, `GET /memories/stats`
- [x] Create `telemetry.py` router file
- [x] `GET /audit`, `GET /telemetry/health`, `GET /system/health`, `GET /system/redis`, `GET /system/database`
- [x] `POST /admin/config`, `POST /admin/mcp/reload`

---

## P1: Next.js Authentication Layer (COMPLETED)
- [x] Install dependencies: `jose`
- [x] Create `web/src/lib/auth.ts` - Auth helper functions
- [x] Create `web/src/app/actions/auth.ts` - Login server action
- [x] Create `web/src/middleware.ts` - Next.js middleware (route protection)
- [x] Create login page `web/src/app/login/page.tsx`
- [x] Add `POST /auth/token` to `app/api/auth.py`
- [x] Add `GET /auth/me` endpoint

---

## P2: Next.js Pages (Core Dashboard)

### Shared Components (COMPLETED)
- [x] Create `Layout.tsx` - Main app layout with sidebar navigation
- [x] Create `MetricCard.tsx` - Reusable metric display component
- [x] Create `DataTable.tsx` - Reusable table component
- [x] Create `LoadingSkeleton.tsx` - Loading states

### Dashboard Page (COMPLETED)
- [x] Create `/dashboard` page
- [x] Display system status metrics (4 cards)
- [x] Quick actions section (Clear Cache, Run Diagnostics)
- [x] Recent activity table (Audit logs)

### Users & IAM Page (COMPLETED)
- [x] Create `/users` page
- [x] User list section
- [x] Create user form
- [x] User details and role info in Layout top bar (Dynamic)
- [ ] User detail view (`/users/[user_id]`)
- [ ] Edit user role/policy form
- [x] User list section
- [x] Create user form
- [ ] User detail view (`/users/[user_id]`)
- [ ] Edit user role/policy form

### Observability & Audit Page (COMPLETED)
- [x] Create `/audit` page
- [x] Audit Logs tab (Paginated table)
- [x] LLM Debug tab (Wire Log toggle)
- [x] Trace Viewer (Placeholder)

### Cortex - Memory & Skills (IN PROGRESS)
- [x] Create `/cortex` page
- [x] Memory Storage tab (List memories, stats)
- [x] Skills Management tab (List skills, stats)
- [x] Evolution History tab (Changelogs, Approve/Reject)
- [ ] Memory Storage tab (List memories, stats)
- [ ] Skills Management tab (List skills, stats)
- [ ] Evolution History tab (Changelogs, Approve/Reject)

---

## P3: Secondary Pages (Lower Priority)
- [ ] Network Status (`web/src/app/network/page.tsx`)
- [ ] Integrations (`web/src/app/integrations/page.tsx`)
