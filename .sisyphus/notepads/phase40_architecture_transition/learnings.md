- Created Plugin and Secret SQLModel models with explicit Relationship back_populates via string Forward References to avoid circular imports.
- Kept missing user back_populate out of Secret to avoid modifying user.py.
- **Database Migrations**: When running alembic autogenerate, if the DB is automatically managed by `SQLModel.metadata.create_all` during container startup, running alembic in the running container will pick up table diffs. We generated `1e981ca9aee9_add_plugin_and_secret_tables.py` for the new `plugin.config` column.

- Implemented _fetch_global_secrets to retrieve and decrypt secrets with scope='global'.
- Updated _load_from_db to include plugin_id in server configuration.
- Injected global secrets into stdio (via env) and sse (via headers) connections.
- Verified that sse_client in mcp library supports headers argument.
