import json
from typing import Optional

from langchain_core.tools import tool

from app.core.decorators import with_user


@tool
@with_user(optional=True)
async def list_available_tools(category: Optional[str] = None, user_id: int = None, **kwargs) -> str:
    """
    List all tools available to the agent, optionally filtered by category.
    Use this to discover what capabilities you have.

    Args:
        category: Optional. Filter by tool category (e.g. 'Core/Internal', 'FILESYSTEM').
                  If None, lists all tools with their categories.
        user_id: User ID (auto-injected)
    """
    from app.core.auth_service import AuthService
    from app.core.worker import AgentWorker

    tools = AgentWorker.get_tools()
    if not tools:
        return "No tools loaded."

    # User object injected by @with_user
    current_user = kwargs.get("user_object")

    # Group by category
    tool_map = {}
    for t in tools:
        # Permission Check
        if current_user:
            # Infer domain/tag if available, else standard
            domain = "standard"
            if hasattr(t, "metadata") and t.metadata:
                domain = t.metadata.get("domain", "standard")

            if not AuthService.check_tool_permission(current_user, t.name, domain):
                continue

        cat = "Core/Internal"
        if hasattr(t, "metadata") and t.metadata and "category" in t.metadata:
            cat = t.metadata["category"]

        if category and category.lower() not in cat.lower():
            continue

        if cat not in tool_map:
            tool_map[cat] = []
        tool_map[cat].append(f"{t.name} - {t.description[:100]}...")

    if not tool_map:
        return f"No tools found matching category '{category}' (or you lack permissions)."

    output = []
    for cat, items in tool_map.items():
        output.append(f"### {cat}")
        for item in items:
            output.append(f"- {item}")

    return "\n".join(output)


@tool
@with_user(optional=True)
async def get_tool_details(tool_name: str, user_id: int = None, **kwargs) -> str:
    """
    Get detailed information about a specific tool, including its arguments validation schema.
    Use this if you are unsure about how to call a tool or what arguments it accepts.

    Args:
        tool_name: The name of the tool to inspect.
        user_id: User ID (auto-injected)
    """
    from app.core.auth_service import AuthService
    from app.core.worker import AgentWorker

    tools = AgentWorker.get_tools()
    target_tool = next((t for t in tools if t.name == tool_name), None)

    if not target_tool:
        return f"❌ Tool '{tool_name}' not found."

    # User object injected by @with_user
    current_user = kwargs.get("user_object")

    # Permission Check
    if current_user:
        domain = "standard"
        if hasattr(target_tool, "metadata") and target_tool.metadata:
            domain = target_tool.metadata.get("domain", "standard")

        if not AuthService.check_tool_permission(current_user, target_tool.name, domain):
            return f"⛔ Permission Denied: You do not have access to view details for '{tool_name}'."

    # Extract schema
    schema = target_tool.args_schema.schema() if target_tool.args_schema else {}

    details = {
        "name": target_tool.name,
        "description": target_tool.description,
        "category": target_tool.metadata.get("category", "Core/Internal")
        if hasattr(target_tool, "metadata")
        else "Unknown",
        "arguments": schema.get("properties", {}),
        "required": schema.get("required", []),
    }

    return json.dumps(details, indent=2, ensure_ascii=False)
