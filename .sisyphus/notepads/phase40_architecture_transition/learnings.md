- Created Plugin and Secret SQLModel models with explicit Relationship back_populates via string Forward References to avoid circular imports.
- Kept missing user back_populate out of Secret to avoid modifying user.py.
- **Database Migrations**: When running alembic autogenerate, if the DB is automatically managed by `SQLModel.metadata.create_all` during container startup, running alembic in the running container will pick up table diffs. We generated `1e981ca9aee9_add_plugin_and_secret_tables.py` for the new `plugin.config` column.

- Implemented _fetch_global_secrets to retrieve and decrypt secrets with scope='global'.
- Updated _load_from_db to include plugin_id in server configuration.
- Injected global secrets into stdio (via env) and sse (via headers) connections.
- Verified that sse_client in mcp library supports headers argument.
- Verified that Global secret injection in app/core/mcp_manager.py has already been implemented correctly by a previous iteration. No further code changes were required.
- **FastAPI Auth Injection**: Created a `require_admin` dependency in `app.core.auth` that chains off `get_current_user` to cleanly enforce admin-only routes at the router/endpoint level, rather than doing inline checks.

### Multi-Tenant MCP Plugin (Crypto Bot)
- **Late-Binding Credentials**: FastMCP throws `InvalidSignature` if a tool parameter explicitly starts with `_` (e.g. `_api_key`). To support late-binding credentials starting with `_` in FastMCP, the tool must accept `**kwargs` and retrieve the injected secrets via `kwargs.get('_api_key')`. This satisfies the injection middleware while avoiding FastMCP's schema validation errors for private-like parameter names.
- **Client Instantiation**: Wrapped tools successfully extracted `_api_key` and `_api_secret` from `kwargs` to pass into `BinanceClientAsync`. The underlying class properly falls back to local environment variables if they are missing or `None`.
- **Plugin Registration**: Demonstrated end-to-end dynamically loading an external MCP server (crypto-bot) by simply inserting a row into the `plugin` table and calling `MCPManager.reload()`, avoiding hard-coded server configurations.
- Verified tool names against actually exposed tools (`get_klines`, `get_account_info`, `get_my_trades`, `get_open_orders`).

### Documentation Update (2026-02-24)
- Updated `docs/progress_report.md` to reflect Phase 40 completion.
- Updated date from 2026-02-21 to 2026-02-24.
- Updated pie chart totals: 31.1 → 32.1 phases, 26 → 27 completed.
- Added new section "🔴 下一代架构转型 (Phase 40) ✅" listing all completed items.
- Documented key transitions: DB-driven plugins/secrets, AES-256 encryption, hot-reloading MCP, late-binding middleware, Next.js frontend scaffold, crypto-bot integration, Docker deployment updates.
- Noted Streamlit deprecation for new features in favor of Next.js.
