# Nexus Agent Project Rules & Standards

This document establishes the coding standards, architectural patterns, and best practices for the Nexus Agent project. All contributors (human and AI) must adhere to these rules to ensure maintainability, security, and scalability.

## 1. Code Reuse & DRY Principle
- **Decorators**: heavily utilize decorators for cross-cutting concerns (Auth, Logging, Permissions).
  - Use `@with_user` via `app.core.decorators` for any tool/function needing `user_id` context.
  - Use `@require_role` for RBAC.
- **Utilities**: Place common logic in `app/core/utils.py` or specific helpers (e.g., `app/core/i18n.py`).
- **Avoid Copy-Paste**: If you find yourself copying logic (especially auth checks or DB session management), refactor it into a shared function or decorator immediately.

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

## 5. Deployment & Configuration
- **Environment Variables**: All config must be in `.env`. Use `os.getenv` with safe defaults.
- **Docker**: improvements must be compatible with `docker-compose.yml`.

## 6. Testing
- **Unit Tests**: New logic requires `pytest` coverage.
- **Integration**: Verification scripts in `scripts/debug/` are encouraged for complex flows.

---
*This file is the source of truth for project standards. Update it as patterns evolve.*
