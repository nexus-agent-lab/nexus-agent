from datetime import datetime
from typing import Callable, List

from langchain_core.tools import tool

from app.core.tool_metadata import build_tool_metadata
from app.core.decorators import require_role
from app.tools.admin_tools import broadcast_notification, restart_system, view_system_logs
from app.tools.automation import list_watch_rules, watch_entity
from app.tools.learning_tools import learn_skill_rule
from app.tools.memory_tools import (
    approve_skill_evolution,
    evolve_memory_skills,
    forget_all_memories,
    forget_memory,
    list_skill_changelog,
    query_memory,
    save_insight,
    store_preference,
)
from app.tools.meta_tools import get_tool_details, list_available_tools
from app.tools.sandbox import get_sandbox_tool
from app.tools.scheduler import delete_task, list_tasks, schedule_task
from app.tools.suggestion_tools import list_suggestions, submit_suggestion, update_suggestion_status


@tool
@require_role("user")
def get_current_time() -> str:
    """Returns the current time in ISO format."""
    return datetime.now().isoformat()


@tool
@require_role("user")
async def schedule_cron_task(cron_expr: str, prompt: str, description: str, **kwargs) -> str:
    """
    Schedules a new recurring task.
    - cron_expr: Standard cron (e.g. '0 9 * * *' for 9am daily)
    - prompt: The text/command to trigger
    - description: Human readable name
    """
    return await schedule_task(cron_expr, prompt, description, **kwargs)


@tool
@require_role("user")
async def list_scheduled_tasks(**kwargs) -> str:
    """Lists all scheduled tasks for the current user."""
    return await list_tasks(**kwargs)


@tool
@require_role("user")
async def remove_scheduled_task(task_id: int, **kwargs) -> str:
    """Deletes a scheduled task by ID."""
    return await delete_task(task_id, **kwargs)


STATIC_TOOL_METADATA = {
    "get_current_time": {
        "capability_domain": "generic",
        "operation_kind": "read",
        "preferred_worker": "chat_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "python_sandbox": {
        "capability_domain": "code_execution",
        "operation_kind": "transform",
        "preferred_worker": "code_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "store_preference": {
        "capability_domain": "memory",
        "operation_kind": "transform",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": False,
    },
    "save_insight": {
        "capability_domain": "memory",
        "operation_kind": "transform",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": False,
    },
    "query_memory": {
        "capability_domain": "memory",
        "operation_kind": "read",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "forget_memory": {
        "capability_domain": "memory",
        "operation_kind": "transform",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "forget_all_memories": {
        "capability_domain": "memory",
        "operation_kind": "transform",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "risk_level": "high",
        "requires_verification": True,
    },
    "learn_skill_rule": {
        "capability_domain": "knowledge",
        "operation_kind": "transform",
        "preferred_worker": "skill_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "schedule_cron_task": {
        "capability_domain": "system",
        "operation_kind": "act",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "list_scheduled_tasks": {
        "capability_domain": "system",
        "operation_kind": "read",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "remove_scheduled_task": {
        "capability_domain": "system",
        "operation_kind": "act",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "watch_entity": {
        "capability_domain": "home_automation",
        "operation_kind": "act",
        "preferred_worker": "skill_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "list_watch_rules": {
        "capability_domain": "home_automation",
        "operation_kind": "read",
        "preferred_worker": "skill_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "restart_system": {
        "capability_domain": "system",
        "operation_kind": "act",
        "preferred_worker": "reviewer_worker",
        "side_effect": True,
        "risk_level": "high",
        "requires_verification": True,
    },
    "broadcast_notification": {
        "capability_domain": "communication",
        "operation_kind": "notify",
        "preferred_worker": "skill_worker",
        "side_effect": True,
        "risk_level": "high",
        "requires_verification": True,
    },
    "view_system_logs": {
        "capability_domain": "system",
        "operation_kind": "read",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "list_available_tools": {
        "capability_domain": "knowledge",
        "operation_kind": "discover",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "get_tool_details": {
        "capability_domain": "knowledge",
        "operation_kind": "read",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "submit_suggestion": {
        "capability_domain": "communication",
        "operation_kind": "notify",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": False,
    },
    "list_suggestions": {
        "capability_domain": "communication",
        "operation_kind": "read",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "update_suggestion_status": {
        "capability_domain": "communication",
        "operation_kind": "act",
        "preferred_worker": "chat_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "evolve_memory_skills": {
        "capability_domain": "knowledge",
        "operation_kind": "transform",
        "preferred_worker": "reviewer_worker",
        "side_effect": True,
        "requires_verification": True,
    },
    "list_skill_changelog": {
        "capability_domain": "knowledge",
        "operation_kind": "read",
        "preferred_worker": "research_worker",
        "side_effect": False,
        "requires_verification": False,
    },
    "approve_skill_evolution": {
        "capability_domain": "knowledge",
        "operation_kind": "act",
        "preferred_worker": "reviewer_worker",
        "side_effect": True,
        "risk_level": "high",
        "requires_verification": True,
    },
}


def _annotate_tool(tool_obj: Callable) -> Callable:
    tool_name = getattr(tool_obj, "name", "")
    metadata = STATIC_TOOL_METADATA.get(tool_name, {})
    tool_obj.metadata = build_tool_metadata(tool_name, metadata)
    return tool_obj


def get_static_tools() -> List[Callable]:
    """Returns the list of static tools."""
    tools = [
        get_current_time,
        get_sandbox_tool(),
        store_preference,
        save_insight,
        query_memory,
        forget_memory,
        forget_all_memories,
        learn_skill_rule,
        schedule_cron_task,
        list_scheduled_tasks,
        remove_scheduled_task,
        watch_entity,
        list_watch_rules,
        restart_system,
        broadcast_notification,
        view_system_logs,
        list_available_tools,
        get_tool_details,
        submit_suggestion,
        list_suggestions,
        update_suggestion_status,
        evolve_memory_skills,
        list_skill_changelog,
        approve_skill_evolution,
    ]
    return [_annotate_tool(tool_obj) for tool_obj in tools]
