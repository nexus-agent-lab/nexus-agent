
### Security - Encrypting Secrets in DB
- **Decision**: Implemented `cryptography.fernet` (AES-256) to handle encryption of sensitive data (like Binance API keys and other user secrets).
- **Implementation**: Created `app/core/security.py` with `encrypt_secret(val)` and `decrypt_secret(val)`. Uses `NEXUS_MASTER_KEY` read directly from `.env`.
- **Rationale**: Fernet provides secure, symmetric encryption that is straightforward to use. `NEXUS_MASTER_KEY` is the only secret allowed in `.env` for the multi-tenant security model. Handled empty and non-encrypted strings gracefully to avoid app crashing on decryption failures.

### Security - Configuration Updates
- **Decision**: Added `NEXUS_MASTER_KEY` example to `.env.example`.
- **Implementation**: Appended the variable and comment to the template to ensure new developers know how to generate and configure the master key.
- The AES-256 encryption engine in `app/core/security.py` using `cryptography.fernet` has been implemented and verified.
- The `NEXUS_MASTER_KEY` has been properly integrated into the `.env` configuration.
- Tests in `tests/unit/test_security.py` pass correctly.
- This serves as the foundation for the multi-tenant secure credential injection.
## MCP Secret Injection Strategy
- Decided to fetch secrets per-plugin during initialization rather than bulk-fetching to keep the  query simple.
- Used internal imports for DB models and security utils to avoid circular dependencies and follow existing patterns in .
## MCP Secret Injection Strategy
- Decided to fetch secrets per-plugin during initialization rather than bulk-fetching to keep the _load_from_db query simple.
- Used internal imports for DB models and security utils to avoid circular dependencies and follow existing patterns in mcp_manager.py.

### Late-Binding Secret Injection Implementation
- **Decision**: Implemented "Late-Binding" Secret Injection in `MCPMiddleware`.
- **Rationale**: Fetching secrets from the database just before calling the tool ensures that sensitive data is only present in memory for the duration of the call and is never cached or logged in plain text.
- **Implementation**:
  - `MCPManager` passes `plugin_id` to `MCPMiddleware` through tool config.
  - `MCPMiddleware._inject_user_secrets` fetches, decrypts, and injects user-scoped secrets into tool arguments.
  - `MCPMiddleware._get_cache_key` filters out injected keys to prevent caching sensitive data.
  - `app.core.audit.mask_secrets` recursively masks common sensitive keys (e.g., `api_key`, `token`) in audit logs.

## Late-Binding Secret Injection Implementation
- **Goal**: Prevent secret leakage in logs and cache keys while allowing sharing of tool results across users.
- **Approach**:
  - Injected secrets are fetched from the database in  just before the tool is called.
  -  was updated to accept  and remove them from the arguments used for hashing.
  -  in  was made robust and recursive to ensure no secrets are leaked in audit logs.
- **Verification**: Tests added/restored in  and  pass, ensuring core logic works as intended.

## Late-Binding Secret Injection Implementation
- **Goal**: Prevent secret leakage in logs and cache keys while allowing sharing of tool results across users.
- **Approach**:
  - Injected secrets are fetched from the database in `MCPMiddleware._inject_user_secrets` just before the tool is called.
  - `_get_cache_key` was updated to accept `injected_keys` and remove them from the arguments used for hashing.
  - `mask_secrets` in `audit.py` was made robust and recursive to ensure no secrets are leaked in audit logs.
- **Verification**: Tests added/restored in `tests/test_mcp.py` and `tests/unit/test_audit.py` pass, ensuring core logic works as intended.

### Secure Input Form & Signed Tokens
- **Decision**: Implemented an ephemeral secure input form to collect sensitive user keys (e.g. Binance Key) without sending them in plain text over Telegram/Feishu.
- **Implementation**: 
  - Created `app/api/secure_input.py` with endpoints to generate links (`/secure/link`), serve forms (`/secure/form/{token}`), and accept submissions (`/secure/submit/{token}`).
  - Used `cryptography.fernet.Fernet` with an ephemeral key generated on application startup to sign and encrypt the payload (`{"user_id": ..., "key": ...}`).
- **Rationale**: 
  - Ephemeral keys naturally invalidate all secure links when the server restarts, adding a layer of security.
  - Relying on Fernet's built-in `ttl` feature during decryption (`ephemeral_fernet.decrypt(..., ttl=600)`) enforces a strict 10-minute expiration for all secure tokens without needing external databases or caches to track token state.
  - Removes the dependency on `NEXUS_MASTER_KEY` for link generation, making the process robust even in unconfigured environments while keeping the actual stored secrets encrypted at rest.

### Frontend - Next.js Adoption
- **Decision**: Initialized a new Next.js project in `web/` using App Router, Tailwind CSS, and TypeScript.
- **Rationale**: Streamlit is being deprecated for new features in favor of a modern, scalable web frontend. Next.js provides better performance, customizability, and developer experience for building out features like the Plugin Marketplace and future UI layers.
- **Implementation**: Created the scaffold with `create-next-app` (using `--skip-install`), configured a basic `PluginMarketplace` page fetching from the FastAPI backend at `http://127.0.0.1:8000/api/plugins/`, and updated the README.
