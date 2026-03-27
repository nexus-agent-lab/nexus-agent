# Phase 40: Next-Gen Architecture Transition (Platform-Level Decoupling)

> **Date**: 2026-02-24
> **Vision**: Transition Nexus Agent from an early script-and-dashboard setup into a fully dynamic, multi-tenant AI Operating System with modern Frontend-Backend separation.

## 1. Core Architectural Shifts

1. **Frontend Transition**: Replace the legacy dashboard with a modern Next.js/React control plane talking to FastAPI.
2. **Plugin & Secret Decoupling**: Move away from `.env` and `mcp_server_config.json`. All system configurations, MCP loading, and secrets will be database-driven, supporting real-time hot-reloading.
3. **Multi-Tenant Security**: Implement a unified `SecretStore` supporting both `Global` (System) and `User` (Private) scopes with AES-256 encryption at rest and "Late-Binding Injection" into the execution context.

---

## 2. Prioritized Roadmap & Execution Plan

### 🚀 [P0] Foundation Layer: Security & Data Models
**Goal**: Establish the secure database foundation before touching any execution logic.

- [x] **Task 1: Unified Data Models**
  - Create `Plugin` model in `app/models/plugin.py` (id, name, type, source_url, status).
  - Create `Secret` model in `app/models/secret.py` (key, encrypted_value, scope: `global|user`, owner_id, plugin_id).
- [x] **Task 2: Encryption Engine**
  - Implement `app/core/security.py` using `cryptography.fernet` (AES-256).
  - Add `NEXUS_MASTER_KEY` to `.env` (the *only* secret that stays in `.env`).
  - Write helper functions: `encrypt_secret(val)`, `decrypt_secret(val)`.
- [x] **Task 3: Alembic Migrations**
  - Generate and apply migrations for the new tables.

### 🔌 [P1] Execution Layer: Dynamic MCP & Injection
**Goal**: Refactor the core engine to boot from the DB and securely inject credentials at runtime.

- [x] **Task 4: Dynamic MCP Loader**
  - Refactor `app/core/mcp_manager.py`.
  - Deprecate `mcp_server_config.json`. The manager must fetch enabled `Plugin` records from the DB.
  - Implement `async def reload()` to hot-swap MCPs without restarting the Docker container.
- [x] **Task 5: Global Secret Injection**
  - When initializing a server, fetch its `Global` secrets from DB, decrypt them, and inject them into the `env` dict for `stdio` or headers for `sse`.
- [x] **Task 6: The "Late-Binding" Middleware**
  - Refactor `MCPMiddleware.call_tool`.
  - Intercept calls, detect `user_id`, fetch matching `User` secrets, decrypt them in memory, and seamlessly inject them into the tool's `arguments`.
  - Ensure Audit logs mask these injected fields.

### 🌐 [P2] Presentation Layer: Frontend-Backend Separation
**Goal**: Build the API surface and the new modern Frontend to manage the OS.

- [x] **Task 7: FastAPI Admin Routes**
  - Build CRUD endpoints in `app/api/plugins.py` and `app/api/secrets.py`.
  - Endpoint for triggering MCP reload: `POST /api/admin/mcp/reload`.
- [x] **Task 8: User "Side-Channel" Secret Input**
  - Create a secure, ephemeral web form (or dedicated API endpoint) where standard users can input their private keys (e.g., Binance Key) without typing them in Telegram.
- [x] **Task 9: Next.js / React Scaffold (New Repo/Folder)**
  - Initialize the new frontend project (e.g., in a `web/` or `frontend/` directory).
  - Build the "Plugin Marketplace" UI (list available plugins, install, configure global secrets).

### 📈 [P3] Ecosystem Layer: Crypto-Bot Integration
**Goal**: Prove the architecture works by deploying the first complex, multi-tenant plugin.

- [x] **Task 10: Crypto-Bot MCP Wrapper**
  - In the `crypto-bot` repo, implement an `mcp_server.py` entrypoint.
  - Refactor its `BinanceClient` to accept credentials dynamically per-request, rather than reading globally from OS environment variables.
- [x] **Task 11: Deployment & Marketplace Listing**
  - Dockerize `crypto-bot` alongside Nexus.
  - Register it in the Nexus Plugin DB.
  - Users securely input their personal `BINANCE_API_KEY` via the new Nexus frontend. Agent executes trades safely.

---

## 3. Transition Strategy Guidelines

1. **Do not break the plane**: While building P0 and P1, the existing `config.json` can still be read as a fallback to ensure current functionality (Home Assistant, Feishu) doesn't break.
2. **Strangler Fig Pattern**: This transition plan has now effectively completed. The active admin surface is the Next.js frontend, and the historical Streamlit dashboard has been removed from the runtime path.
