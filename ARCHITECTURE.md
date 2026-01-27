# Nexus Agent Architecture

## 1. System Overview

Nexus Agent is a private, high-performance intelligent control center designed for **Apple Silicon (M4)** hardware. It prioritizes data privacy by running all critical inference and memory operations locally.

**Core Philosophy:**
- **Local-First**: LLM and Embeddings run on-device (Ollama, Metal/MPS).
- **Active Memory**: The agent doesn't just "log" chats; it actively distills and retrieves "Insights" and "Preferences".
- **Secure**: Application-level permissions (RBAC) and Audit Logging for all tool executions.

---

## 2. High-Level Architecture

The system is composed of four main Dockerized services communicating via a private network:

```mermaid
graph TD
    User[User / Client] -->|HTTP/Voice| API[Nexus Agent API (FastAPI)]
    
    subgraph "Local Infrastructure (Docker)"
        API -->|Generate| LLM[Ollama (Qwen2.5-14B)]
        API -->|Embed/Search| Embed[Embedding Server (bge-small-zh)]
        API -->|Read/Write| DB[(PostgreSQL + pgvector)]
        API -->|Cache| Redis[(Redis)]
    end
    
    subgraph "External/Local Tools"
        API -->|MCP Protocol| MCPServer[Local Scripts / MCP Servers]
        API -->|Sandboxed Exec| Sandbox[Docker Sandbox]
    end
```

---

## 3. Core Components

### 3.1 Agent Core (LangGraph)
The agent's "brain" is a state machine built with **LangGraph**, following a `Think -> Act -> Observe` loop.

*   **State**: `messages`, `user_context`, `memories`, `trace_id`.
*   **Nodes**:
    1.  **Retrieve Memories**: Fetches relevant context from `pgvector` based on the user's latest query.
    2.  **Model**: Calls the Local LLM (Qwen2.5) with the injected context and available tools.
    3.  **Tools**: Executes requested tools (with permission checks) and returns outputs.
*   **Edge**: loops back to **Model** if a tool was called; ends if a final answer is generated.

### 3.2 Active Memory System
Unlike standard RAG, this system differentiates between memory types:
*   **Profile**: Static facts about the user (e.g., "Lives in Shanghai", "Uses Python").
*   **Reflexion**: Insights derived from past interactions (e.g., "User prefers concise answers").
*   **Knowledge**: General stored facts.

**Technical Stack**:
*   **Storage**: PostgreSQL with `pgvector` extension.
*   **Index**: HNSW (Hierarchical Navigable Small World) for fast ANN search.
*   **Embedding**: `BAAI/bge-small-zh-v1.5` hosted on a local FastAPI server, accelerated by Mac Metal (MPS).
*   **Retrieval**: Cosine similarity search (Default threshold: 0.4).

### 3.3 Model Context Protocol (MCP)
The agent connects to external capabilities via MCP.
*   **Registry**: Tools are defined in `mcp_server_config.json`.
*   **Security**: Each tool execution is gated by an **Audit Interceptor** that logs the attempt, checks RBAC permissions (e.g., specific tools require `admin` role), and records the result.

---

## 4. Data Flow

### Chat Request Lifecycle
1.  **Ingestion**: User sends a message via HTTP POST `/chat`.
2.  **Authentication**: API Key is validated; User identity is attached to the request.
3.  **Memory Retrieval**:
    *   System embeds the user's message using the Local Embedding Server.
    *   Queries `pgvector` for top-k relevant memories (Sim > 0.4).
    *   Injects memories into the System Prompt: *"You know the following about the user..."*
4.  **Reasoning**:
    *   LLM receives message + memory context.
    *   Decides to call a tool (e.g., `save_insight`) or answer directly.
5.  **Execution (if Tool selected)**:
    *   Agent checks if User has permission for the tool.
    *   Tool is executed (e.g., saving a new vector to DB).
    *   Result is fed back to LLM.
6.  **Response**: Final answer is returned to the user.

---

## 5. Directory Structure

```text
/app
  /core
    agent.py       # LangGraph definition
    memory.py      # MemoryManager (Vector DB logic)
    mcp.py         # MCP Client & Tool loading
    audit.py       # Audit Logging Interceptor
  /models
    user.py        # SQLModel for User/Auth
    memory.py      # SQLModel for Vectors
  /tools
    memory_tools.py # save_insight, store_preference
    registry.py     # Static tool registration
/scripts
    deploy_local.sh # One-click startup (Ollama + Embedding + App)
    verify_memory_zh.py # Chinese Verification Script
/servers
    demo_tool.py    # Example MCP server
```
