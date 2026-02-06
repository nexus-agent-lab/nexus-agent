# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands
- **Install Dependencies**: `uv pip install -r requirements.txt` (uses `uv` for management)
- **Linting**: `ruff check app/ scripts/ --select E,F,I --ignore E501`
- **Run All Tests**: `PYTHONPATH=. pytest tests/ -v`
- **Run Single Test File**: `PYTHONPATH=. pytest tests/test_filename.py -v`
- **Run Single Test Case**: `PYTHONPATH=. pytest tests/test_filename.py -k "test_name" -v`
- **Dev Check Script**: `bash scripts/dev_check.sh` (Runs Ruff and Pytest)
- **Database Migrations**: `alembic upgrade head`
- **Docker Deployment**: `docker-compose up -d --build`

## Architecture Overview
Nexus Agent is an "AI Operating System" centered around an LLM "CPU" and LangGraph orchestration.

- **Nexus Kernel (`app/core/agent.py`)**: A LangGraph state machine orchestrating the "Listen -> Think -> Act -> Reflexion" loop.
- **Interface Layer (`app/interfaces/`)**: Adapters (Telegram, Feishu) that translate platform-specific events into `UnifiedMessage` formats.
- **Message Queue (`app/core/mq.py`)**: Decouples the Interface Layer from the core processing logic.
- **Agent Worker (`app/core/worker.py`)**: Consumes MQ messages and invokes the LangGraph agent.
- **MCP Manager (`app/core/mcp_manager.py`)**: Dynamically manages tools via the Model Context Protocol.
- **Memory System (`app/core/memory.py`)**: Uses PostgreSQL with `pgvector` for semantic and long-term memory.
  - **Extension**: Ensure `CREATE EXTENSION vector` is run before tables (handled in `db.py`).
  - **Embeddings**: Uses **Ollama** (`bge-m3`, 1024 dim) on port 11434 by default.
- **Mission Control (`dashboard/`)**: Streamlit-based dashboard for observability, IAM, and memory management.

## Key Patterns and Constraints
- **LLM Initialization**: Always use `app/core/llm_utils.py` for instantiating LLM and embedding clients.
- **Embeddings**: Default model is `bge-m3:latest` (1024 dim). Do not fallback to 512-dim `bge-small` usage without DB reset.
- **Tool Security**: Tools accessing user data MUST use the `@with_user` decorator and accept a `user_id`.
- **Error Handling**: Tools should return descriptive error strings instead of raising exceptions to enable Agent self-recovery.
- **Cross-cutting Concerns**: Use decorators like `@require_role` for access control.
- **Git Protocol**: Do not skip hooks; ensure `bash scripts/dev_check.sh` passes before committing.
- **Network**: Local dev uses Docker Bridge (no Tailscale auth required). Ports 8000/8501 exposed directly.
