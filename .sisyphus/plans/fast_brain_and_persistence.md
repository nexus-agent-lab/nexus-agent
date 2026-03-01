# Work Plan: Fast Brain & WireLog Persistence

## Objective
Implement the "Fast Brain" (Tier 0 Intent Router) to handle complex, cross-domain queries efficiently. Simultaneously, migrate the transient "WireLog" system (DEBUG_WIRE_LOG) to a persistent Database-backed architecture to prevent loss of settings and traces on restart.

## Scope
- **IN**: Implement `app/core/intent_router.py`.
- **IN**: Refactor `agent.py` and `tool_router.py` to use multi-intent routing.
- **IN**: Create `LLMTrace` database model.
- **IN**: Implement `TraceLogger` to save logs to DB.
- **IN**: Update `admin.py` to persist system settings in the `SystemSetting` table.
- **IN**: Restore settings from DB on startup in `main.py`.

## Implementation Steps

### Phase 1: Fast Brain (Intent Router) [COMPLETED]
1. **Create `app/core/intent_router.py`**: A lightweight LLM call (zero tools) to decompose user queries into keywords. [x]
2. **Update `app/core/tool_router.py`**: Add `route_multi()` to handle multiple intent strings and merge vector results. [x]
3. **Integrate into `app/core/agent.py`**: Use `intent_router` before tool selection to build a more accurate tool belt. [x]

1. **Create `app/core/intent_router.py`**: A lightweight LLM call (zero tools) to decompose user queries into keywords. [x]
2. **Update `app/core/tool_router.py`**: Add `route_multi()` to handle multiple intent strings and merge vector results. [x]
3. **Integrate into `app/core/agent.py`**: Use `intent_router` before tool selection to build a more accurate tool belt. [x]

### Phase 2: WireLog Persistence (Backend)
1. **Create `app/models/llm_trace.py`**: Define the `LLMTrace` SQLModel. [x]
2. **Run Migrations**: [x]
   `docker-compose exec -T nexus-app alembic revision --autogenerate -m "add_llm_trace"`
   `docker-compose exec -T nexus-app alembic upgrade head`
3. **Create `app/core/trace_logger.py`**: A utility to write traces to the DB asynchronously. [x]

1. **Create `app/core/intent_router.py`**: A lightweight LLM call (zero tools) to decompose user queries into keywords. [DONE]
2. **Update `app/core/tool_router.py`**: Add `route_multi()` to handle multiple intent strings and merge vector results. [DONE]
3. **Integrate into `app/core/agent.py`**: Use `intent_router` before tool selection to build a more accurate tool belt. [DONE]

1. **Create `app/core/intent_router.py`**: A lightweight LLM call (zero tools) to decompose user queries into keywords. [DONE]
18#NS|2. **Update `app/core/tool_router.py`**: Add `route_multi()` to handle multiple intent strings and merge vector results. [DONE]

2. **Update `app/core/tool_router.py`**: Add `route_multi()` to handle multiple intent strings and merge vector results.
3. **Integrate into `app/core/agent.py`**: Use `intent_router` before tool selection to build a more accurate tool belt.

### Phase 2: WireLog Persistence (Backend) [COMPLETED]
1. **Create `app/models/llm_trace.py`**: Define the `LLMTrace` SQLModel. [x]
2. **Run Migrations**: [x]
3. **Create `app/core/trace_logger.py`**: A utility to write traces to the DB asynchronously. [x]
4. **Update `app/api/admin.py`**: [x]
   - Refactor `POST /config` to write to `SystemSetting` table.
   - Add `GET /traces` to retrieve logs.
5. **Update `app/main.py`**: Add a startup task to load `DEBUG_WIRE_LOG` from DB into `os.environ`. [x]

### Phase 3: Agent & UI Integration
1. **Refactor `app/core/agent.py`**: Replace `print()` statements with calls to `trace_logger`. [x]
2. **Update UI components**: Ensure settings are fetched/saved to the new persistent endpoints.

1. **Create `app/models/llm_trace.py`**: Define the `LLMTrace` SQLModel.
2. **Run Migrations**: 
   `docker-compose exec -T nexus-app alembic revision --autogenerate -m "add_llm_trace"`
   `docker-compose exec -T nexus-app alembic upgrade head`
3. **Create `app/core/trace_logger.py`**: A utility to write traces to the DB asynchronously.
4. **Update `app/api/admin.py`**: 
   - Refactor `POST /config` to write to `SystemSetting` table.
   - Add `GET /traces` to retrieve logs.
5. **Update `app/main.py`**: Add a startup task to load `DEBUG_WIRE_LOG` from DB into `os.environ`.

### Phase 3: Agent & UI Integration
1. **Refactor `app/core/agent.py`**: Replace `print()` statements with calls to `trace_logger`.
2. **Update UI components**: Ensure settings are fetched/saved to the new persistent endpoints.

## Quality Assurance
- Run `bash scripts/dev_check.sh`.
- Verify multi-intent queries (e.g., "Check temperature and write to Feishu") in logs.
- Verify `DEBUG_WIRE_LOG` persists after `docker-compose restart`.
