## Cleanup of app/core/mcp_manager.py
- Removed deprecated `_load_config()` and `_expand_env_vars()` methods.
- Removed `self._config` property from `__init__`.
- Removed unused `_DEFAULT_CONFIG_PATH` and `CONFIG_PATH` constants.
- Verified that the file still compiles correctly.
