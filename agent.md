# Nexus Agent - Context Handoff & Developer Guide

> **Target Audience**: AI Agents (Claude, OpenHands, etc.) and Human Developers.
> **Purpose**: Provides a complete state dump, architectural constraints, and next actions to seamlessly continue development.

---

## 1. Project Overview
**Nexus Agent** is a private intelligent operating system where the LLM acts as the CPU. It is built on a microservices architecture using **Docker**, **FastAPI**, **LangGraph**, and **PostgreSQL**.

- **Core Philosophy**: "LLM as CPU, Tools as Peripherals."
- **Key Protocol**: Uses **MCP (Model Context Protocol)** for all tool interactions.
- **Observability**: Raw LLM Request/Response logging via `httpx` hooks and explicit prints in `agent.py`.
- **Identity Scope**: Supports multi-user contexts (Home vs. Enterprise) with strict RBAC.

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

## 3. Critical Development Rules (DO NOT IGNORE)
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

## 4. Current State (As of 2026-01-31)
**Phase 24 & 25 Completed**:
- **Product Suggestion System**:
    - Model: `ProductSuggestion` (DB Table).
    - Tools: `submit_suggestion`, `list_suggestions`, `update_suggestion_status`.
    - UI: `dashboard/pages/6_Roadmap.py` (Kanban/List view).
- **Telegram I18n**:
    - The bot command menu (`start`, `help`, `bind`) now auto-syncs to the user's language (EN/ZH).

**Active Issues Resolved**:
- Fixed `asyncpg` "operation in progress" concurrency error in Dashboard by refactoring session management.
- Fixed `ValueError` in tools due to missing docstrings (caused by incorrect decorator nesting).

---

## 5. Roadmap & Todo List

### Phase 26: Enhanced Self-Evolution (Planned)
- [ ] **Code Self-Repair**: Allow the agent to read `dev_check.sh` output and auto-fix lint errors (agent-on-agent).
- [ ] **Knowledge Graph**: Upgrade memory from flat vector search to GraphRAG (Neo4j or PG-Graph).

### Phase 27: Multi-Modal Capabilities
- [ ] **Image Analysis**: Integration with GPT-4o-Vision for processing Telegram `PhotoSize` objects.
- [ ] **Voice Support**: TTS/STT pipeline for Telegram Voice Notes.

### Phase 28: Enterprise Connectors
- [ ] **DingTalk Integration**: Similar to Feishu, implement `app/interfaces/dingtalk.py`.
- [ ] **Email/Calendar MCP**: Bi-directional sync for Office365/Google.

---

## 6. How to Resume Work
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

## 7. Key File Locations
- **Agent Logic**: `app/core/agent.py` & `app/core/worker.py`
- **Tool Registry**: `app/tools/registry.py`
- **Dashboard**: `dashboard/pages/`
- **Testing**: `tests/` and `scripts/debug/`

---
*Generated for seamless context handover.*
