# Nexus Agent Architecture

## 1. Project Overview

### What is Nexus Agent?
Nexus Agent is a **private, local-first intelligent control center** for your digital life. Unlike cloud-based assistants (like ChatGPT or Claude), Nexus Agent runs entirely on your own hardware (optimized for **Apple Silicon M-series**), ensuring that your personal data, memories, and tool interactions never leave your device.

### Core Capabilities & Scenarios

| Capability | Description | Usage Scenario |
| :--- | :--- | :--- |
| **Active Memory** | Remembers user preferences and facts over time using vector storage. | *Reflexion*: "You previously told me you prefer Python. I will write this script in Python." |
| **Local Reasoning** | Runs powerful LLMs (Qwen2.5-14B) locally via Ollama. | *Privacy*: Summarizing sensitive documents or managing financial data without cloud API calls. |
| **Tool Execution** | Connects to local files, scripts, and APIs via MCP (Model Context Protocol). | *Automation*: "Read my latest log file and summarize the errors." |
| **Voice Interface** | Supports speech-to-text and text-to-speech. | *Hands-free*: "Hey Nexus, take a note about this meeting." |

---

## 2. High-Level Architecture

The system is designed as a **Modular Agentic Loop**. It is composed of four main Dockerized services communicating via a private network.

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

### Key Design Decisions
1.  **Local-First & Privacy**: We chose **PostgreSQL + pgvector** instead of a cloud vector DB to keep the stack simple and unified. All inference happens on `localhost`.
2.  **Hardware Acceleration**: The Embedding Server uses **MPS (Metal Performance Shaders)** to run efficient semantic search on Mac chips.
3.  **Active Memory**: This isn't just a chat log. The agent actively decides to *save* or *retrieve* specific insights, creating a growing knowledge base.

---

## 3. Core Components Breakdown

### 3.1 Agent Core (The Brain)
The agent's logic is a state machine built with **LangGraph**. It doesn't just reply; it loops:
`Think -> Retrieve Context -> Plan -> Act -> Observe -> Reply`.

*   **State Machine**: Tracks conversation history, user context, and current tool outputs.
*   **Security**: Every action is checked against an **RBAC Policy** (Role-Based Access Control) before execution.

### 3.2 Active Memory System (The Hippocampus)
We categorize long-term memory into three distinct types to improve retrieval quality:

*   **👤 Profile**: Static facts about you (e.g., "Lives in Shanghai", "Manager role").
*   **💡 Reflexion**: Behavioral insights (e.g., "User prefers concise code").
*   **📚 Knowledge**: General stored facts or file summaries.

**Technical Flow**:
1.  User sends a message.
2.  System generates a vector embedding locally (`bge-small-zh`).
3.  Queries `pgvector` for memories with **similarity > 0.4**.
4.  Injects relevant memories into the prompt before the LLM sees the message.

### 3.3 Model Context Protocol (The Hands)
Nexus Agent uses the **MCP Standard** to use tools. This allows it to:
*   Connect to standard MCP servers (like a Postgres viewer or File System access).
*   Run local Python scripts securely.
*   **Audit Interceptor**: A middleware layer that logs every single tool call to the database (`auditlog` table) for transparency.

---

## 4. Data Flow Example

**Scenario**: User says *"Save a note that I'm moving to Tokyo next month."*

1.  **Ingestion**: HTTP POST `/chat` receives the text.
2.  **Authentication**: API Key validated. User ID resolved.
3.  **Retrieval**: System checks `pgvector` for existing context (e.g., "Where does user live now?").
4.  **Reasoning (LLM)**:
    *   LLM sees the input and decides: *I need to use the `store_insight` tool.*
    *   LLM generates arguments: `{"content": "User is moving to Tokyo next month", "type": "profile"}`.
5.  **Execution**:
    *   Agent verifies user permissions.
    *   `MemoryManager` embeds the text and saves it to DB.
6.  **Response**: Agent confirms action: *"I've updated your profile to reflect your move to Tokyo."*

---

## 5. Developer Guide

### Directory Structure
*   **`/app/core`**: The engine room. `agent.py` (Graph), `memory.py` (Vector Logic), `mcp.py` (Tools).
*   **`/app/models`**: SQLModel database definitions.
*   **`/scripts`**: Utilities. Use `deploy_local.sh` to start everything.

### Extending the Agent
To add a new capability:
1.  Create a Python function in `servers/demo_tool.py`.
2.  Add it to `mcp_server_config.json`.
3.  Restart the agent. The LLM will automatically discover the new tool.
