# Nexus Agent

Nexus Agent is a private, multimodal intelligent control center powered by a Local LLM (or API) as its core computing unit. Optimized for **Apple Silicon (M4)**, it ensures maximum privacy and performance by running reasoning and memory entirely on-device.

## 🚀 Key Features

-   **Privacy-First Reasoning**: Native support for **Ollama (Qwen2.5-14B)** running locally on your Mac.
-   **Active Memory**: Vectorized long-term memory using **pgvector** and a local embedding server (**bge-small-zh**) with **MPS (Metal)** hardware acceleration.
-   **MCP Integration**: Full support for the **Model Context Protocol**, allowing the Agent to interact with local scripts and enterprise tools.
-   **Multimodal**: Voice interaction capabilities (STT/TTS) and sandbox execution for secure code tasks.
-   **Governance**: Built-in Audit Interceptor for tracking every tool call and decision.

## 🛠️ Prerequisites

-   **Hardware**: Mac with Apple Silicon (Recommended: M4 with 32GB+ RAM).
-   **Software**: Docker, Python 3.10+, and Homebrew.

## 📦 Quick Start (Local Deployment)

The easiest way to get started is using the automated deployment script:

1.  **Clone & Configure**:
    ```bash
    cp .env.example .env
    # Edit .env if you want to use cloud providers as fallback
    ```

2.  **Launch All Services**:
    This script starts Ollama (LLM), the Embedding Server, and the Nexus Agent.
    ```bash
    ./scripts/deploy_local.sh
    ```

3.  **Chat with the Agent**:
    ```bash
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -H "X-API-Key: test-admin-key-123" \
      -d '{"message": "Remember that I prefer building with Python and Tailwind CSS"}'
    ```

## 🏗️ Architecture

For a detailed deep-dive into the system components, data flow, and active memory implementation, please read the [Architecture Documentation](ARCHITECTURE.md).

-   **LLM**: Ollama / Qwen2.5-14B (Local) or GLM-4/GPT-4 (Cloud).
-   **Memory**: PostgreSQL + `pgvector` (512-dim).
-   **Embeddings**: `bge-small-zh-v1.5` hosted on a local FastAPI server with Metal acceleration.
-   **Orchestration**: LangGraph for complex agentic workflows and tool-calling loops.

## 📂 Project Structure

-   `app/core/`: Application core (Agent State, MemoryManager, MCP client).
-   `app/tools/`: Static tools (Registry) and dynamic tools (Memory, Sandbox).
-   `scripts/`: Deployment and verification utilities.
-   `servers/`: Directory for custom MCP server scripts.
-   `alembic/`: Database migrations.

## 🧪 Verification

To ensure your local memory system is functioning correctly:
```bash
python scripts/verify_memory.py
```
