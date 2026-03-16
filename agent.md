# Nexus Agent - Context Handoff & Developer Guide

> **Target Audience**: AI Agents (Claude, OpenHands, etc.) and Human Developers.
> **Purpose**: Provides a complete state dump, architectural constraints, and next actions to seamlessly continue development.

---

## 1. Project Overview
**Nexus Agent** is a self-hosted, governable Agent control plane for home and enterprise environments. It is built on a microservices architecture using **Docker**, **FastAPI**, **LangGraph**, and **PostgreSQL**.

- **Core Philosophy**: "LLM as CPU, Tools as Peripherals."
- **Key Protocol**: Uses **MCP (Model Context Protocol)** for all tool interactions.
- **Observability**: Raw LLM Request/Response logging via `httpx` hooks and explicit prints in `agent.py`.
- **Identity Scope**: Supports multi-user contexts (Home vs. Enterprise) with strict RBAC/ABAC.
- **Default Deployment Model**: One Nexus deployment per home or team, many users accessing it through messaging apps or lightweight web entry points.
- **Product Direction**: Optimize for private deployment, shared use, permissions, audit, and low-friction mobile-first interaction rather than desktop-only developer workflows.

### 2. Architecture & Tech Stack
| Component | Technology | Description |
| :--- | :--- | :--- |
| **Orchestration** | `LangGraph` | State machine for Agent loop (Listen -> Think -> Route -> Act -> Reflexion). |
| **API/Gateway** | `FastAPI` | REST API for frontend and webhooks. |
| **Database** | `PostgreSQL` + `pgvector` | User data, memory, and semantic knowledge retrieval. |
| **Identity** | `Redis` + `AuthService` | Session management and Bind Tokens for Telegram/Feishu. |
| **Frontend** | `Streamlit` | Admin Dashboard (`dashboard/`) for management and visualization. |
| **Async Runtime** | `asyncio` + `uvloop` | High-concurrency async execution (critical for Streamlit/DB). |

---

## 3. Architectural Direction (Critical Context)

When making product or architecture decisions, assume the following:

1. **Single deployment, multi-user access**
   - Nexus is not primarily a per-user local tool.
   - A family or organization should deploy it once and let many users access the same service.

2. **Mobile-first and messaging-first**
   - Most users will interact through WeChat, Telegram, Feishu, DingTalk, or mobile-friendly web UI.
   - Do not assume every user has a laptop, terminal, or server access.

3. **Binding is a core capability**
   - Identity binding from external messaging account -> Nexus user -> family/team/org scope is product-critical.
   - Do not treat bind flows as a side feature.

4. **Home and enterprise share one foundation**
   - Home use cases: family memory, reminders, Home Assistant, device control.
   - Enterprise use cases: internal MCP integration, approvals, workflow communication, audit.
   - Both should be built on the same foundations: identity, permissions, memory, actions, and audit.

5. **Governance over breadth**
   - Prefer permission boundaries, auditability, safe MCP integration, and execution control over adding many loosely governed capabilities.
   - Do not default to broad third-party skill execution without isolation and policy controls.

6. **Low-friction user experience first**
   - Prioritize simpler login, easier onboarding, and better messaging entry points over technically pure but high-friction developer setup.

For strategic context, also read:

- `docs/project_focus_and_direction.md`
- `docs/architecture/mcp_governance.md`
- `docs/architecture/identity_system.md`

---

## 4. Critical Development Rules (DO NOT IGNORE)
Refer to `PROJECT_RULES.md` for the full list.
1.  **Verification**: ALWAYS run `bash scripts/dev_check.sh` after *any* modification. It runs `ruff` (lint/format) and `pytest`.
2.  **Decorators**:
    - Use `@with_user()` (factory pattern with parens!) for tools requiring user context.
    - Use `@require_role("admin")` for privileged tools.
3.  **Streamlit Async**:
    - **NEVER** use `asyncio.run()` directly inside Streamlit pages.
    - **ALWAYS** use the `run_async(coro)` helper (check `dashboard/pages/6_Roadmap.py` for implementation) to avoid event loop conflicts.
4.  **Database & MCP**:
    - Use `async with AsyncSessionLocal() as session:`.
    - Dashboard files must use `from utils import ...` instead of `from dashboard.utils ...`.
    - **MCP Lifecycle**: `MCPManager` is loop-sensitive. Dashboard MUST use fresh instances and call `await mcp.cleanup()`.

---

## 5. Current State (Strategic)

Current priority is not broad feature expansion. It is to make Nexus genuinely useful for:

- the author
- the author's family
- a small number of trusted colleagues

Current top priorities:

- improve login and permission experience
- reduce setup friction around messaging access
- add or prioritize more natural mobile-facing entry points
- make Home Assistant control reliable
- validate family memory/reminder workflows
- gather real enterprise needs for internal MCP onboarding and workflow integration

Current anti-goals:

- do not optimize first for a broad AI OS narrative
- do not prioritize a large open skill marketplace
- do not assume unrestricted third-party execution is acceptable
- do not overbuild enterprise features before real onboarding signals exist

### LangGraph Branch Status

The `codex/langgraph-migration-plan` line should now be treated as a **usable execution baseline** rather than an open-ended refactor track.

- The runtime already has worker-aware routing, normalized tool/reviewer outcomes, explicit `verify/report/clarify/repair` follow-up paths, and dispatcher-owned recovery semantics.
- This is enough to support near-term P0 scenario validation, especially around Home Assistant reliability and governed execution.
- Further work on this line should be driven by real P0 needs. Do not continue pure graph/subgraph refactoring unless it directly improves Home Assistant reliability, permissions, binding/login friction, or mobile/message usability.

### Latest P0 Reliability Snapshot

As of the latest `main` progress:

- Home Assistant control flow has been tightened so explicit control requests do not stop at discovery-only state.
- Ambient temperature questions such as "家里冷不冷" and "哪个房间最高/最低" now have a runtime guardrail that filters appliance/process sensors before the model sees the entity list.
- `homeassistant.restart` is currently restricted to `admin` as a temporary runtime guardrail.

These are deliberate P0 reliability patches. They are acceptable for the current phase, but they are **not** the final ownership boundary. The intended future direction is:

- move Home Assistant-specific business policy into declarative plugin / skill policy
- keep core graph logic generic
- keep runtime enforcement reading from config/metadata instead of accumulating ad hoc hardcoded rules

### New-Session Resume Point

If a new session starts now, the most useful continuation point is:

1. validate remaining `P0-1` Home Assistant reliability scenarios
   - permission denied
   - entity not found
   - abnormal / unavailable device state
2. record a failure checklist from real runs
3. only then move to `P0-2` binding / login / permission UX

Do **not** restart pure LangGraph refactoring unless a concrete P0 issue forces it.

---

## 6. Near-Term Roadmap

### P0: Access and Identity
- [ ] Improve login flow and permission UX.
- [ ] Make account binding simpler and more reliable.
- [ ] Reduce Telegram friction and treat it as a technical channel rather than the only main entry.
- [ ] Explore WeChat or other more family-usable messaging entry points.

### P0: Home AI Center Core Loop
- [ ] Make Home Assistant integration reliable for real daily use.
- [ ] Support family-member permission boundaries.
- [ ] Ensure core device control and status queries are auditable.

### P1: Family Memory
- [ ] Implement lightweight family memory and reminder flows.
- [ ] Support reminder memory, arrival-triggered memory, preference memory, and household task memory.

### P1: Enterprise Foundation
- [ ] Define better MCP/internal system onboarding patterns.
- [ ] Strengthen permission declarations and execution contracts.
- [ ] Improve audit patterns for enterprise-facing workflows.

### Explicit Reminder for Agents
- Before proposing major new features, ask whether they improve the shared multi-user, mobile-first, self-hosted control-plane direction.
- If a change mainly benefits a single technical operator but increases complexity for normal users, treat it as lower priority unless explicitly requested.

---

## 7. How to Resume Work
1.  **Start Environment**:
    ```bash
    docker-compose up -d
    ```
2.  **Verify State**:
    ```bash
    bash scripts/dev_check.sh
    ```
3.  **Check Task List**:
    - Read `task.md` for granular sub-tasks.
    - Read `walkthrough_v2.md` to understand recent changes.

## 8. Key File Locations
- **Agent Logic**: `app/core/agent.py` & `app/core/worker.py`
- **Tool Registry**: `app/tools/registry.py`
- **Dashboard**: `dashboard/pages/`
- **Testing**: `tests/` and `scripts/debug/`

---
*Generated for seamless context handover.*
