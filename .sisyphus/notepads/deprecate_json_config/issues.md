
- Found and resolved leftover duplicate logic in `app/core/mcp_manager.py` during refactoring (lines 167-169 and 205-219, plus duplicate class attributes and `get_system_instructions` definitions) which caused `IndentationError` during parsing.
