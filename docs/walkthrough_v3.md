# Semantic Tool Routing Walkthrough

## Summary
We implemented Semantic Tool Routing to solve the "Too many tools" context limit issue and improve LLM performance. The system now dynamically selects the top-K most relevant tools for each user query using local embeddings (BGE-M3/Ollama).

## 1. 🧠 Semantic Router
- **Component**: `app/core/tool_router.py`
- **Logic**:
    - **Core Tools**: Always available (Time, Memory, Sandbox).
    - **Semantic Tools**: Ranked by cosine similarity between query and tool description embeddings.
- **Model**: `bge-m3:latest` via Ollama (port 11434).
- **Performance**: Reduced context window from ~35 tools to ~10 tools per turn.
- **Multilingual**: Verified support for both English ("Check temperature") and Chinese ("查下家里的温度") via BGE-M3 model capabilities.

## 2. ⚡ Agent Integration
- **Dynamic Binding**: `agent.py` now calls `router.route(query)` before binding tools.
- **Preserved State**: If router fails or returns empty, falls back to ALL tools (safety net).

## 3. 👁️ Observability & Debugging
- **ASCII Flow Trace**: When `DEBUG_WIRE_LOG=true` is set, the logs visualize the decision process:
```text
User Query: "Check temperature"
  │
  ▼
① call_model (agent.py)
  │
  ├─ tool_router.route("Check temperature...")
  │   ├─ Embedding Query -> Cosine Similarity
  │   │  ├─ [MATCH] entity_action             (score=0.5186)
  │   │  ├─ [MATCH] get_history               (score=0.5095)
  │   │  ├─ [MATCH] search_entities_tool      (score=0.4987)
  │   └─ Selected: 5 Core + 5 Semantic = 10 Total
```
- **Admin API**: `POST /admin/config` to toggle `DEBUG_WIRE_LOG` at runtime without restart.
- **Container Logs**: The ASCII trace is printed to stdout for easy viewing via `docker logs`.

## 4. 🛠️ Fixes & Cleanups
- **Project Structure**: Standardized routers by moving `admin.py` to `app/api/`.
- **Attributes**: Fixed `AttributeError` by properly importing `CORE_TOOL_NAMES` in `agent.py`.
- **Docs**: Updated `task.md` and `implementation_plan.md`.

## Verification Status
- [x] Router selects HA tools for "temperature" (EN/ZH).
- [x] Core tools present in selection.
- [x] ASCII trace visible in Docker logs.
- [x] Admin API updates config dynamically.
