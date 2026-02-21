# Task: Skill System Architecture Implementation ✅

## Phase 1: Skills Directory ✅
- [x] Create `skills/` directory structure
- [x] Create `_template.md` with comprehensive format
- [x] Create `homeassistant.md` skill card
  - [x] Core capabilities
  - [x] Critical rules (盲人规则, 模糊匹配, 大数据处理)
  - [x] 3 few-shot examples
  - [x] Tool usage patterns
  - [x] Best practices and common mistakes
- [x] Create `python_sandbox.md` skill card

## Phase 2: Core Components ✅
- [x] Implement `SkillLoader` class
  - [x] `load_all()` - Load all skill cards
  - [x] `load_by_name()` - Load specific skill
  - [x] `list_skills()` - List with metadata
  - [x] `save_skill()` - Save/update skills
  - [x] YAML frontmatter parsing
- [x] Implement `SkillGenerator` class
  - [x] Configurable LLM support (OpenAI, Anthropic, Local)
  - [x] `generate_skill_card()` - AI-powered generation
  - [x] Fallback template for errors
  - [x] Optional anthropic import handling

## Phase 3: Agent Integration ✅
- [x] Modify `app/core/agent.py`
  - [x] Import `SkillLoader`
  - [x] Load skill cards in `create_agent_graph()`
  - [x] Inject skills into system prompt
  - [x] Maintain backward compatibility with MCP instructions

## Phase 4: API Endpoints ✅
- [x] Create `app/api/skills.py` router
  - [x] `GET /skills/` - List all skills
  - [x] `GET /skills/{name}` - Get skill content
  - [x] `POST /skills/generate` - Generate skill card
  - [x] `PUT /skills/{name}` - Save/update skill
  - [x] `DELETE /skills/{name}` - Delete skill
  - [x] Admin role protection for write operations
- [x] Register router in `app/main.py`

## Phase 5: Configuration ✅
- [x] Update `.env.example`
  - [x] Add `SKILL_GEN_PROVIDER` configuration
  - [x] Add `SKILL_GEN_MODEL` configuration
  - [x] Add `SKILL_GEN_API_KEY` configuration
  - [x] Document all options

## Phase 6: Testing ✅
- [x] Create `tests/test_skill_loader.py`
  - [x] Test skills directory exists
  - [x] Test load all skills
  - [x] Test load specific skill
  - [x] Test list skills with metadata
  - [x] Test metadata extraction
  - [x] Test save/delete operations
  - [x] Integration test with agent
- [x] Verify all existing tests still pass (26/26 ✅)

## Phase 7: Documentation ✅
- [x] Resolve linting compliance without ignoring imports
- [x] Update documentation and walkthrough
- [x] Implement Telegram `/unbind` command
- [x] Enforce one-to-one identity binding (strict mode)
- [x] Debug "no response" issue in `bind_command`
- [x] Ensure command menu updates in both local and BotFather mode document
- [x] Update task checklist

## Phase 7: Telegram Advanced Features (Moltbot-Inspired)
- [x] Implement HTML Safe Fallback (robust sending)
- [x] Add automatic message chunking (>4096 chars)
- [ ] Port smart ID normalization regex
- [ ] Add `telegram_react` tool for native emojis

## Phase 8: Multi-Language Support (I18n)
- [x] Add `language` field to User model (default: "en")
- [x] Implement `I18n` helper class with EN/ZH strings
- [x] Update Telegram `start`, `help`, `bind`, `unbind` to use localized strings
- [x] Update `run_telegram_bot` to sync menus for both `en` and `zh`
- [x] **Memory Retrieval**: Implement `query_memory` tool for explicit retrieval (Approved).

## Future Work (Phase 9+)
- [ ] Implement Voice Interaction (STT/TTS)
- [ ] Add Multi-Modal Support (Image/File Uploads)
- [x] Dashboard Integration
  - [x] Add skill editor UI to `dashboard/pages/5_Integrations.py`
  - [x] "Generate Skill Card" button with LLM selection
  - [x] Live preview and editing interface
- [x] MCP Config Migration
  - [x] Add `skill_file` field to `mcp_server_config.json`
  - [x] Deprecate inline `system_instruction`
- [ ] Production Testing
  - [ ] Test with real Home Assistant instance
  - [ ] Validate effectiveness with GLM-4.7-Flash
  - [ ] Iterate on few-shot examples
- [ ] MCP Cache Layer (Future)
  - [ ] Implement Redis/memory cache
  - [ ] Add TTL configuration per tool
  - [ ] Cache invalidation strategies

## **Phase 5: Stability & Reliability**
    - [x] Fix Agent Recursion Loop in Temperature Queries ✅
        - [x] Increase `prune_tool_output` threshold to 2000 chars in `session.py`
        - [x] Improve JSONL detection in `mcp_middleware.py`
        - [x] Add `recursion_limit` to `agent.py` and handle error in `stream_agent_events`

## Phase 9: Session Memory (Local Optimization) ✅
- [x] Define Session/SessionMessage models in `app/models/session.py`
- [x] Implement SessionManager in `app/core/session.py` (load/save/prune)
- [x] Integrate with `agent.py` (load history at start, save interactions)
- [x] Verify with `scripts/debug/verify_session.py`

## Phase 10: System Prompt Refactoring (Generic Core) ✅
- [x] Remove hardcoded Home Assistant references from `app/core/agent.py`
- [x] Generalize "Tool Domain Awareness" section in core prompt
- [x] Verify `homeassistant.md` skill card covers removed rules

## Phase 11: Optimizations (Two-Stage Skill Loading) ✅
- [x] Investigate recursion/loading issues
- [x] Implement `SkillLoader.load_summaries()` for lightweight indexing
- [x] Implement `Dynamic Skill Injection` logic in `agent.py`
- [x] Update skill cards with `intent_keywords`
- [x] **OpenClaw Research & Adaptation** (User Context, Silent/Thinking)

## Phase 21: Self-Evolution System (Inspired by OpenClaw) ✅
    - [x] **User Context Injection**: Dynamic System Prompt with `timezone`, `notes` (DB + PromptBuilder)
    - [x] **Menu Auto-Sync (P1)**: Update Telegram commands based on user language.
    - [x] **Skill Marketplace (P2)**: Basic `skill_registry.json`, `/skill` admin command, ClawHub integration.
    - [ ] **Hooks System (P3)**: Event-driven architecture for advanced customization (e.g., Soul Swap)
    - [ ] **Media/File Handling (P4)**: Improved support for voice/images in chat
    - [x] **Silent Protocol**: Implement `NO_REPLY` token for group chat sanity
    - [x] **Thinking Visibility**: Stream "Thinking..." status/content to Telegram UI

## Phase 22: Security Enhancements (TODO)
    - [ ] **Skill Audit Mechanism**: Preview skill content before install, require Admin confirmation
    - [ ] **Command Sandbox**: Whitelist allowed domains/commands for shell/curl tools
    - [ ] **Tool-Level Permissions**: Fine-grained control over what tools each skill can invoke

## Phase 23: MemSkill Memory System (In Progress)
    - [x] **MemorySkill Model**: Created `models/memory_skill.py` with MemorySkill + MemorySkillChangelog
    - [x] **Base Skills**: Created 4 skills in `skills/memory/` (fact_extraction, preference_capture, semantic_search, exact_match)
    - [x] **MemorySkillLoader**: File-based loading + DB sync logic
    - [x] **MemoryController**: Keyword matching + LLM fallback for skill selection
    - [ ] **MemoryManager Integration**: `add_memory_with_skill()` and `search_memory_with_skill()`
    - [ ] **Tool Updates**: Modify memory_tools.py to use new flow
    - [ ] **Designer**: Implement skill evolution logic
    - [ ] **Dashboard**: Designer audit log UI

## Phase 24: Session Auto-Compacting (P0.5) ✅
    - [x] **SessionSummary Model**: Create model to store summarized history
    - [x] **Summarization Logic**: Implement `compact_session()` background task
    - [x] **Context Assembly**: Update `get_history()` to return Summary + Recent Messages
    - [x] **Cron Job**: Triggered via `save_interaction_node` (background task)

## Phase 25: GLM 4.7 Flash Performance Optimization (Done) ✅
    - [x] **System Prompt 瘦身**: Reduced from ~2K to ~1K tokens
    - [x] **Compact 智能触发**: Only compact when unarchived > threshold (20)
    - [x] **Memory 检索按需**: Skip vector search for short/simple messages
    - [x] **Wire Logging 可控**: Gated debug prints behind `DEBUG_WIRE_LOG`
    - [x] **MemSkill Tool 接入**: Wired memory_tools.py to `add_memory_with_skill`


## Phase 12: Self-Learning System (Audit & Remediation) ✅
- [x] Create `SkillChangelog` database model
- [x] Implement `learn_skill_rule` tool (Auto/Manual logic)
- [x] Create API endpoints for Log/Approve/Reject
- [x] Update Dashboard with "Skill Learning Audit" UI
- [x] Verify End-to-End Learning Flow

## Phase 13: Deployment Enhancements ✅
- [x] Add Dashboard to Docker Compose
- [x] Expose ports on `ts-nexus` for local access
- [x] Expose ports on `ts-nexus` for local access
- [x] Configure Dashboard to use local Docker network
- [x] Verify system health with `pytest` (Resolved DB locking issues)

## Phase 14: Open Source Prep - Phase 1: Security & Sanitization ✅
- [x] Scan and remove hardcoded secrets (`sk-`, tokens, IPs)
- [x] Normalize environment variables (BaseSettings, `.env.example`)
- [x] Refactor absolute paths to relative (`pathlib`)
- [ ] Clean Git history of sensitive files/data (User Instruction)

- [ ] Clean Git history of sensitive files/data (User Instruction)

## Phase 15: Open Source Prep - Phase 2: Project Structure & Standards ✅
- [x] Standardize `pyproject.toml` (Metadata, Ruff, Pytest)
- [x] Consolidate dependency management
- [x] Verify tool configuration
- [x] **Project Rules**: Created `PROJECT_RULES.md` to codify development standards (DRY, Architecture).
- [x] Consolidate dependency management
- [x] Verify tool configuration

## Phase 16: Open Source Prep - Phase 3: Documentation & Onboarding ✅
- [x] Create comprehensive `README.md`
- [x] Add `LICENSE` (MIT)
- [x] Document Quick Start & Architecture

## Phase 17: Open Source Prep - Phase 4: CI/CD & GitHub Actions ✅
- [x] Create `.github/workflows/ci.yml`
- [x] Configure automated Linting & Testing

## Phase 19: Enterprise Integration - Feishu (Lark) ✅
- [x] Research Feishu Bot Event Subscription (WebSocket vs Webhook)
- [x] Implement `app/interfaces/feishu.py` (Push to Inbox)
- [x] Update `app/core/dispatcher.py` for Feishu support
- [ ] Test message round-trip (Requires App ID/Secret)

## Phase 20: Identity System (Multi-User) ✅
- [x] **Database**: Create `UserIdentity` model & Migration
- [x] **API**: Implement `POST /api/auth/bind-token` (Redis-backed)
- [x] **Bot Logic**: Implement `/bind` command handler (Telegram/Feishu)
- [x] **Auth**: Replace Env-based `ALLOWED_USERS` with DB lookup
- [x] **UI**: Add "Integrations" management to Dashboard

## Phase 21: Telegram UX Enhancements
- [x] **Live Status System**: Implement message pinning and real-time updates for agent thought process.
- [x] **Onboarding Flow**: Improve reply for unbound/guest users with clear binding instructions.
- [x] **Interactive Bind**: Support `/bind` without arguments (prompts for token).
- [x] **Dynamic Menus**: Implement mechanism to sync allowed skills to Telegram Command Menu (per user).
- [x] **Admin Management**: Restricted skills/tools to admins and added proactive system alerts.
- [x] **Autonomous Memory**: LLM now proactively saves/corrects preferences without user intervention.

## Phase 22: Advanced Tooling & Governance (Meta-System) ✅
- [x] **Agent Self-Correction**: Implemented tool name auto-patching to fix hallucination loops.
- [x] **Bulk Actions**: Added `forget_all_memories` for efficient memory management.
- [x] **Tool Discovery**: Implemented `list_available_tools` and `get_tool_details` for agent introspection.
- [x] **Permission Enforcement**: Enhanced discovery tools to respect User RBAC policies (Admin/Standard).

## Phase 23: Enterprise Integration - DingTalk
- [ ] Implement `app/interfaces/dingtalk.py`
- [ ] Support DingTalk outgoing webhooks/events
- [ ] Test message round-trip

## Phase 22: Sandbox Artifacts & Visualizations (Code Interpreter)
- [ ] Infrastructure: Mount `/artifacts` and add data libs
- [ ] Tool: Update Sandbox for file detection
- [ ] UI: Update Message Adapters for photo/URL delivery

### Optimization & Scalability
- [ ] **Hierarchical Tool Discovery (Router)**: Implement a two-step tool loading mechanism (Router -> Skill Tools) to handle 100+ tools.
  - *Note*: addresses scalability but risks latency. Requires UX optimization (e.g., optimistic UI).

## Phase 20: Sandbox Artifacts & Visualizations (Roadmap)
- [ ] Infrastructure: Mount `/artifacts` and add data libs
- [ ] Tool: Update Sandbox for file detection
- [x] Bug Fix: Telegram 'typing...' internal status leaking as text message (Investigate)
- [ ] UI: Update Telegram for photo/URL delivery

## Phase 24: Product Suggestion System (Innovation) ✅
- [x] **Database**: Create `ProductSuggestion` model (content, status, votes, tags).
- [x] **Tool**: Implement `submit_suggestion` tool for users.
- [x] **Dashboard**: Add "Roadmap" page for admin review/status updates.
- [ ] **Self-Reflection**: Support retrieval of "approved" suggestions for future coding tasks.

## Phase 25: UX Refinements ✅
- [x] **Telegram I18n**: Synchronize dynamic menu commands with user language preference.

## Phase 26: Testing & Quality Assurance (Current) ✅
- [x] **Unit Tests**: Create `tests/unit/test_suggestion_tools.py` covering model and tools.
- [x] **Integration Tests**: Create `tests/integration/test_product_flow.py` verifying full suggestion lifecycle.
- [x] **Dashboard Tests**: Verify `dashboard/pages/6_Roadmap.py` logic (mocked DB).

## Phase 27: Observability & RELIABILITY ✅
- [x] **LLM Wire Logging**: Implement raw request/response logging in `app/core/agent.py` (Sync & Async supported).
- [x] **Dashboard Reliability**: Fix `ModuleNotFoundError` for dashboard imports and solve `RuntimeError` (event loop mismatch) by using loop-safe session creation.
- [x] **MCP SSE Stability**: Solve `RuntimeError` (cancel scope mismatch) in SSE client by refactoring `MCPManager` to be loop-aware and isolating it in Dashboard pages.
- [x] **Health Check**: Ran `dev_check` and fixed all regressions (indentation, imports, test-loop conflicts).
- [x] **Telegram Progress Updates**: Implemented real-time "progress board" for Telegram.
    - [x] Initial "Thinking" message removed as per user request (classic typing used).
    - [x] Discrete tool updates (Start/End) showing results.
- [x] **LLM & Embeddings Connectivity**: Fixed `APIConnectionError` by injecting robust `httpx` clients with timeouts and `trust_env=True`.
    - [x] **Smart Proxy Fallback**: Automatically use `TELEGRAM_PROXY_URL` if `HTTP_PROXY` is missing, solving Docker connectivity issues.
    - [x] **Safety Check**: fallback only applies to HTTP/HTTPS schemes to prevent crashes with SOCKS.
    - [x] **Local Connection Bypass**: Prevents proxy fallback for local destinations (`host.docker.internal`, `localhost`) by setting `trust_env=False` to ignore system proxies.
    - [x] **Sync Fallback**: Switched `memory.py` to use synchronous `embed_query` in `asyncio.to_thread` to completely bypass async `httpx` connection issues with local Docker services.
    - [x] **Client Simplification**: Removed all injected `httpx` clients from `agent.py` and `memory.py` to restore stable default behavior.
    - [x] **Root Cause Discovery**: Confirmed via host-side `curl` that the embedding service on port 9292 is **DOWN** (Connection refused). This is an external dependency issue, not a code issue.
    - [x] **Embeddings Migration**: Fully migrated configuration to use **Ollama** (`bge-m3`, port 11434) instead of the deprecated custom script.
        - [x] Updated `docker-compose.yml` defaults.
        - [x] Updated `.env.example` & `README.md` for proper documentation.
    - [x] **Network Simplification**: Temporarily disabled Tailscale (`ts-nexus`) to reduce dev friction.
        - [x] Decoupled `nexus-app` and `dashboard` from Tailscale network mode.
        - [x] Exposed ports 8000 and 8501 directly to host.
        - [x] Updated Dashboard `API_URL` for internal bridge networking.
    - [x] **Database Stabilization**: Fixed `type "vector" does not exist` error by ensuring `CREATE EXTENSION` runs before table creation in `db.py`.
    - [x] **Documentation Update**: Updated `CLAUDE.md` to reflect new architecture (Ollama embeddings, Bridge network, DB initialization).
    - [x] **Streaming Optimization**: Disabled LLM streaming (`streaming=False`) to simplify network flow, while retaining "Thought/Tool" event updates for Telegram.
- [x] **Engineering Excellence (DRY)**: Centralized `httpx` client creation logic in `app/core/llm_utils.py` (Retention only, currently unused in core flows).
- [x] **Engineering Excellence (DRY)**: Centralized `httpx` client creation logic in `app/core/llm_utils.py`.
    - [x] Refactored `agent.py` and `memory.py` to use shared utilities.
    - [x] Added enforcement rule to `PROJECT_RULES.md`.

---
## Phase 28: Device Control Extensions (Planned)
- [ ] **Android Control (ADB)**: MCP server for controlling Android phones via USB/WiFi.
    - [ ] Basic tools: screenshot, tap, swipe, input text, launch app
    - [ ] WeChat automation strategy (Vision LLM + coordinate tapping)
- [ ] **Desktop Control**: MCP server for Mac/Windows automation.
    - [ ] PyAutoGUI-based screen interaction
    - [ ] AppleScript integration (Mac)
    - [ ] PowerShell integration (Windows)
- [ ] **Security**: Admin-only access, device allowlist, audit logging


## Phase 29: Semantic Tool Routing (Performance) ✅
- [x] **Router Logic**: Implemented `SemanticToolRouter` using `BGE-M3` (local/Ollama) for multilingual tool matching.
- [x] **Agent Integration**: Updated `agent.py` to dynamically bind top-K relevant tools per turn.
- [x] **Core Protection**: Defined `CORE_TOOL_NAMES` that are always available (sandbox, memory, time).
- [x] **Observability**: Added `DEBUG_WIRE_LOG` ASCII flow tracing in `agent.py` to visualize routing decisions.
- [x] **Admin Controls**: Created `/admin/config` and `/admin/log` endpoints to toggle logging and view traces.

## Phase 30.1: Routing Precision & System Logs (P0)
- [x] **Role-Aware Router**: Add `role` param to `tool_router.route()`, filter admin-only tools for non-admin users
- [x] **Context-Aware Routing**: Use last 2-3 messages (not just last one) for query disambiguation
- [x] **`view_system_logs` Tool**: New admin-only tool to read app/Docker logs
- [x] **System Management Skill Update**: Add log-related keywords and examples to `system_management.md`
- [x] **Verification**: Confirm "查看系统日志" routes correctly per role
- [x] **Ad-Hoc Fixes & Improvements** (User Request)
  - [x] Implement `ondelete="CASCADE"` for Memory & UserIdentity models
  - [x] Fix `NameError` (variable scope) and `SyntaxError` (indentation) in `app/core/agent.py`
  - [x] Resolve `dev_check.sh` issues (imports sorting, test linting, SQLModel indexing)
  - [x] Refactor Exception Handling in `agent.py` (Rule: No Global Try/Except)
  - [x] Implement Auto-Suggestion for Missing Capabilities (P1)
  - [/] Implement Skill Hierarchy (P2) [OpenViking Mode: Semantic Routing]
    - [x] Hierarchical Skill Loading (Vector Router)
    - [ ] Event Trigger System (Battery Watch)
