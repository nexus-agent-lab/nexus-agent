from datetime import datetime
from typing import Callable, List

from langchain_core.tools import tool

from app.core.decorators import require_role
from app.tools.admin_tools import broadcast_notification, restart_system
from app.tools.learning_tools import learn_skill_rule
from app.tools.memory_tools import forget_memory, query_memory, save_insight, store_preference
from app.tools.sandbox import get_sandbox_tool
from app.tools.scheduler import delete_task, list_tasks, schedule_task


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


def get_static_tools() -> List[Callable]:
    """Returns the list of static tools."""
    return [
        get_current_time,
        get_sandbox_tool(),
        store_preference,
        save_insight,
        query_memory,
        forget_memory,
        learn_skill_rule,
        schedule_cron_task,
        list_scheduled_tasks,
        remove_scheduled_task,
        restart_system,
        broadcast_notification,
    ]
