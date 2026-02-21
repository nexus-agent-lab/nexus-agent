# Project Nexus Development Tasks

## Setup (Environment Preparation)
- [x] Create project folder structure (/app, /core, /tools, /tests) <!-- id: 0 -->
- [x] Write requirements.txt (fastapi, langgraph, langchain-openai, pydantic, uvicorn) <!-- id: 1 -->
- [x] Write docker-compose.yml (Python App + Redis) <!-- id: 2 -->
- [x] Git: Initialize repository and commit changes <!-- id: 19 -->

## Phase 1: MVP Prototype
- [x] Core: Define AgentState data structure (Pydantic) <!-- id: 3 -->
- [x] Core: Implement LLMNode and graph logic (LangGraph) <!-- id: 4 -->
- [x] Tools: Implement ToolRegistry and basic tools (get_current_time, calculate_number) <!-- id: 5 -->
- [x] API: Create FastAPI /chat endpoint to run the graph <!-- id: 6 -->

## Phase 2: Core Implementation (Governance & Persistence)
- [x] Infrastructure: Update docker-compose with Postgres (pgvector) & requirements.txt <!-- id: 7 -->
- [x] Models: Define SQLModel schemas (User, Context, Tool, AuditLog) <!-- id: 8 -->
- [x] Auth: Implement API Key validation and User retrieval dependency <!-- id: 9 -->
    - [x] Intelligent Proxy: Middleware with Caching & Rate Limiting (mcp_middleware.py)
    - [x] Optimization: Dynamic System Prompt (Tool grouping).
    - [ ] Optimization: Dynamic Instruction Injection (Per-MCP Prompts)
        - [ ] Goal: Inject instructions from `mcp_server_config.json`.
        - [ ] Feature: **Auto-Generate Prompt**: During MCP installation, call LLM to generate "Best Practices" based on tool definitions.
    - [x] Optimization: Switch to Cloud LLM (GLM-4) for better instruction following.
    - [x] **Prompt & Data Optimization** <!-- id: 4 -->
    - [x] Refactor System Prompt to "Universal Kernel" (remove HA specific overfitting) <!-- id: 5 -->
    - [x] Enhance Middleware Prompt (`mcp_middleware.py`) to guide `python_sandbox` code generation <!-- id: 6 -->
        - [x] Implement "Teacher Mode" with JSON/Text distinction <!-- id: 13 -->
        - [x] Add Fuzzy Match instructions <!-- id: 14 -->
    - [x] Verify Data Source Quality (`list_entities`) <!-- id: 7 -->
        - [x] Check if `attributes` (friendly_name) are returned <!-- id: 15 -->
        - [x] Validate `python_sandbox` execution prevents "String Matching Trap" <!-- id: 16 -->
    - [ ] Create `domain_registry.yaml` for dynamic rule injection (Future work) <!-- id: 8 -->
    - [ ] Optimization: Error Sanitization <!-- id: 56 -->
    - [ ] Goal: Prevent internal system errors (SQL, formatting) from leaking to LLM.
    - [ ] Implementation: Catch known system exceptions in `agent.py` and return generic error tokens.
    - [ ] Optimization: MCP Server Descriptions <!-- id: 55 -->
    - [ ] Goal: Inject high-level server description (e.g., "Home Assistant: Control smart devices") into Prompt.
    - [ ] Implementation: Extract `server_info` during MCP handshake in `mcp_manager.py`.
    - [x] Optimization: Token Reduction for Tool Defs <!-- id: 57 -->
        - [ ] Goal: Deduplicate/Simplify schemas for parameter-less tools.
        - [ ] Strategy: Adopt `moltbot` pattern:
            - **Schema Normalization**: Flatten `anyOf`/`oneOf`, strip unsupported keywords (like `clean-for-gemini.ts`).
            - **Concise System Prompt**: List tools as `- Name: Summary` only (like `system-prompt.ts`), move full schema to API call (optimized).
            - **Filter**: Only expose relevant tools.
    - [x] Fix: Resolve Zod Incompatibility in Home Assistant MCP <!-- id: 58 -->
        - [x] Root Cause: Zod v4.3.5 incompatible with `zod-to-json-schema`, resulting in empty schemas.
        - [x] Solution: Clean reinstall with Zod v3.25.1 + SDK v1.25.3.
        - [x] Verification: All tool schemas correctly populated. E2E test passed.
    - [ ] Optimization: Formatting & Log Cleanup <!-- id: 64 -->
        - [x] Format LLM JSON Input/Output for readability.
        - [ ] Disable noisy OpenAI debug logs.
    - [x] Optimization: Token Reduction for Tool Defs <!-- id: 57 -->
        - [x] Schema Normalization: Flatten `anyOf`/`oneOf`, strip unsupported keywords.
- [x] Audit: Implement asynchronous Audit logging (Interceptor/BackgroundTasks) <!-- id: 16 -->

## Phase 3: Advanced Features
...
- [ ] Feature: **Streaming Output (Real-time Progress)** <!-- id: 65 -->
    - [ ] API: Implement `/chat/stream` using Server-Sent Events (SSE).
    - [ ] Logic: Use `astream_events` to capture intermediate thoughts and tool results.
    - [ ] Integration: Update Telegram Bot to push chunks incrementally.- [x] Sandbox: Implement SandboxExecutor (docker-py) <!-- id: 11 -->
- [x] Voice: Add /voice endpoint (Whisper/TTS) <!-- id: 12 -->
- [x] MCP: Support Model Context Protocol <!-- id: 22 -->
- [x] Active Memory: Active Memory Architecture (Vectorized) <!-- id: 24 -->
    - [x] Model: Define `Memory` SQLModel with `pgvector` (512 dimensions)
    - [x] Service: Implement `MemoryManager` (Embedding + Search)
    - [x] Integration: Auto-retrieval in Agent Graph
    - [x] Bug Fixes: Duplicate startup, logger import, dimension config
    - [x] Local Deployment: Ollama + bge-small-zh scripts
    - [x] Migration: Apply dimension update to database
    - [x] Tools: Implement `save_insight` and `store_preference`
    - [x] Verification: End-to-end memory lifecycle test
    - [ ] Feature: **Context Pruning (Summarization Memory)** <!-- id: 59 -->
        - [ ] Goal: Reduce token usage in long conversations.
        - [ ] Strategy: Keep System Prompt & User Query. Summarize completed tool chains and replace raw logs with `LLM Summary`.
- [x] Phase 3 Complete <!-- id: 130 -->
## Phase 4: Enterprise & Network (The "Nexus Network")
- [x] Networking: Integrate **Tailscale (tsnet)** for zero-config mesh networking <!-- id: 25 -->
    - [x] Infrastructure: Add Sidecar container (docker-compose)
    - [x] Feature: "Home" vs "Work" context switching based on network tags.
    - [x] Feature: Seamless mobile/desktop connection without port forwarding.
- [x] Context Kernel: Implement **Context & Auth Manager** <!-- id: 26 -->
    - [x] Auth: strict RBAC middleware (Context-Aware Access Control).
    - [x] Policy: `Tag:Home` vs `Tag:Enterprise` tool isolation.
- [x] Intelligence: Implement **Reflexion (Self-Correction)** Node <!-- id: 13 -->
    - [x] Logic: Feedback loop in LangGraph (Act -> Reflexion -> Think).
- [x] Dashboard: Nexus Command Center (v2) <!-- id: 14 -->
    - [x] Foundation: Streamlit + SqlAlchemy init.
    - [x] **Mission Control**: System Overview & Health Metrics.
    - [x] **IAM**: User Management & Policy Visualizer.
    - [x] **Observability**: Trace Viewer & Reflexion Inspector.
    - [x] **Cortex**: Memory Manager & Semantic Search.
    - [x] **Network**: Tailscale Node Visualization.
- [x] Phase 4 Complete <!-- id: 140 -->

## Phase 5: Integration Hub (MCP Ecosystem)
- [x] MCP Manager: Hot-Reload & Lifecycle <!-- id: 50 -->
    - [x] Upgrade `mcp_server_config.json` to support multi-server registry.
    - [x] Implement `MCPManager` class with `install()` and `reload()` methods.
    - [x] Support local directory mount for development.
- [x] Dashboard: Integrations Page <!-- id: 51 -->
    - [x] Create `5_Integrations.py` for managing MCP Servers.
    - [x] Implement "Add from Git URL" workflow (UI Skeleton).
- [x] Adapter: HomeAssistant MCP <!-- id: 52 -->
    - [x] Develop `servers/ha_mcp.py` (Used Hybrid Mode: `mcp-homeassistant` Node.js).
    - [x] Register in `mcp_server_config.json`.
- [ ] Adapter: Read-Only DB MCP <!-- id: 53 -->
    - [ ] Create `servers/postgres_readonly.py`.
- [x] Interface: Telegram Bot (Mobile) <!-- id: 54 -->
    - [x] Dependency: `python-telegram-bot` added to requirements.
    - [x] Logic: `app/interfaces/telegram.py` implemented.
    - [x] Security: User ID Whitelist implemented.
    - [x] Feature: **Real-time Progress Sync** <!-- id: 63 -->
        - [x] Callback: `stream_agent_events` in `agent.py` for real-time tracking.
        - [x] API: `POST /chat/stream` (SSE) implemented in `main.py`.
        - [x] UI: Telegram bot refactored to use message editing for progress.
        - [x] Cleanup: OpenAI debug logs reduced; test scripts organized in `tests/`.


## Phase 6: Nexus Dynamic Registry (Multi-Agent Core)
- [ ] Architecture: Sub-Graph Orchestration <!-- id: 60 -->
    - [ ] Goal: Implement efficient Multi-Agent routing (Router -> Specialist).
    - [ ] Design: `docs/dynamic_registry_architecture_zh.md`.
- [ ] Feature: MCP Onboarding Protocol <!-- id: 61 -->
    - [ ] Logic: Auto-generate System Prompts via GPT-4o upon MCP installation.
    - [ ] Storage: `data/registry.json` for persisted agent personas.
- [ ] Feature: Runtime Supervisor <!-- id: 62 -->
    - [ ] Logic: L1 Router Node (Intent Classification).
    - [ ] Logic: L2 Specialist Node Factory (Context Switching).

