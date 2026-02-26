# Nexus Agent Project Rules & Standards

This document establishes the coding standards, architectural patterns, and best practices for the Nexus Agent project. All contributors (human and AI) must adhere to these rules to ensure maintainability, security, and scalability.

## 1. Code Reuse & DRY Principle
- **Decorators**: heavily utilize decorators for cross-cutting concerns (Auth, Logging, Permissions).
  - Use `@with_user` via `app.core.decorators` for any tool/function needing `user_id` context.
  - Use `@require_role` for RBAC.
- **Utilities**: Place common logic in `app/core/utils.py` or specific helpers (e.g., `app/core/i18n.py`).
- **Avoid Copy-Paste**: If you find yourself copying logic (especially auth checks or DB session management), refactor it into a shared function or decorator immediately.
- **LLM/Embeddings Clients**: ALWAYS use centralized utilities in `app/core/llm_utils.py` (e.g., `get_httpx_client`) to ensure standardized timeouts, proxy support (trust_env), and logging.

## 2. Architecture & Patterns
- **Service Layer**: Business logic resides in `app/core/{service}.py` (e.g., `auth_service.py`, `memory.py`).
- **Interface Layer**: Platform-specific adapters stay in `app/interfaces/{platform}.py`. They must **not** contain core business logic, only data translation.
- **Dependency Injection**: Use `get_session()` or `AsyncSessionLocal` context managers. Do not pass DB sessions distinctively unless necessary for transactions.
- **DTOs**: Use Pydantic models for data exchange, especially for Tool arguments and API schemas.

## 3. Tool Development
- **Meta-Data**: 
  - All tools must have clear docstrings.
  - Use `metadata` in `StructuredTool` to tag `category` and `domain`.
- **Permissions**:
  - Tools accessing user data MUST accept `user_id: int`.
  - Use `@with_user` to automatically resolve the `User` object.
  - Check permissions using `AuthService.check_tool_permission` if the tool accesses restricted domains.

## 4. Error Handling
- **Graceful Failures**: Tools should return descriptive error strings (e.g., "❌ Error: ...") rather than raising exceptions, so the Agent can recover.
- **Logging**: Use `logger = logging.getLogger("nexus.{module}")`. Log important state changes at INFO, detailed debugging at DEBUG.
- **No Global Try/Except**: Do not wrap large blocks of code in catch-all `try...except Exception`. This masks coding errors (like `NameError`).
  - Only use `try...except` for specific runtime risks (e.g., Network I/O, API calls).
  - Let coding errors crash so they can be caught by `dev_check.sh` or during local testing.

## 5. Deployment & Configuration
- **Environment Variables**: All config must be in `.env`. Use `os.getenv` with safe defaults.
- **Docker**: improvements must be compatible with `docker-compose.yml`.

## 6. Testing
- **Unit Tests**: New logic requires `pytest` coverage. Run with `uv run pytest`.
- **Git Commits**: After completing any major modification or feature, you MUST run tests (`bash scripts/dev_check.sh`). If tests pass, you MUST immediately create a git commit with a descriptive message.
- **Integration**: Verification scripts in `scripts/debug/` are encouraged for complex flows.
- **Git Hooks**: **NEVER** skip pre-commit hooks (e.g. `git commit --no-verify`). Fix the underlying issue (linting/tests) instead.
- **Verification**: Always run `bash scripts/dev_check.sh` after making changes to ensure code quality.

## 7. Logic Retention & Stability
- **No Unauthorized Deletions**: Do NOT delete existing logic or features unless explicitly requested by the user. 
- **评估与询问 (Assess & Ask)**: If you discover existing logic that appears obsolete, redundant, or incorrect, you must first assess the impact and **ask the user for confirmation** before removing it.
- **Stick to the Plan**: Modifications must strictly follow the approved development plan. Do not perform large-scope incidental refactorings or "cleanup" without permission.
- **Preserve Traceability**: Maintain debugging aids like `wireLog` even during major refactors. If a block must move, ensure it is re-integrated rather than discarded.
- **Preserve Comments**: NEVER delete existing comments, docstrings, or developer notes. Historical context is critical for long-term maintenance.
- **Frontend Verification**: If changes are detected in the `web/` directory, `dev_check.sh` will trigger `docker-compose build web` (which runs `npm run build`). This ensures that frontend breaking changes are caught before commit.

- **Strict Syntax Verification**: Every modification MUST pass `python3 -m py_compile` locally. This is integrated into `dev_check.sh` and is a mandatory pre-commit gate. This prevents IndentationErrors and SyntaxErrors from reaching the repository.

---
*This file is the source of truth for project standards. Update it as patterns evolve.*
