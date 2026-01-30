import logging
from typing import Optional

from pydantic import BaseModel, Field
from sqlmodel import select

from app.core.db import AsyncSessionLocal
from app.core.scheduler import SchedulerService
from app.models.scheduler import ScheduledTask
from app.models.user import User

logger = logging.getLogger("nexus.tools.scheduler")

class ScheduleTaskArgs(BaseModel):
    cron_expr: str = Field(description="Cron expression (e.g. '0 9 * * *' for daily at 9am)")
    prompt: str = Field(description="The prompt or action to trigger when the time comes")
    description: str = Field(description="A short, human-readable description of this task")

async def schedule_task(cron_expr: str, prompt: str, description: str, **kwargs) -> str:
    """
    Schedules a new recurring task for the current user.
    """
    user: Optional[User] = kwargs.get("user")
    channel_id: Optional[str] = kwargs.get("channel_id")
    channel: Optional[str] = kwargs.get("channel")

    if not user or not channel_id or not channel:
        return "Error: Missing user or channel context. Scheduling failed."

    try:
        scheduler = SchedulerService.get_instance()
        new_task = ScheduledTask(
            user_id=user.id,
            channel=channel,
            channel_id=channel_id,
            cron_expr=cron_expr,
            description=description,
            task_type="prompt",
            payload={"prompt": prompt},
            enabled=True
        )

        await scheduler.add_task(new_task)
        return f"✅ Successfully scheduled task: '{description}' with schedule '{cron_expr}'."
    except Exception as e:
        logger.error(f"Failed to schedule task: {e}")
        return f"❌ Failed to schedule task: {str(e)}"

async def list_tasks(**kwargs) -> str:
    """
    Lists all active scheduled tasks for the current user.
    """
    user: Optional[User] = kwargs.get("user")
    if not user:
        return "Error: User context not found."

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScheduledTask).where(ScheduledTask.user_id == user.id)
        )
        tasks = result.scalars().all()

        if not tasks:
            return "You have no scheduled tasks."

        output = ["Your Scheduled Tasks:"]
        for t in tasks:
            status = "🟢 Enabled" if t.enabled else "🔴 Disabled"
            output.append(f"- ID {t.id}: **{t.description}** ({t.cron_expr}) - {status}")
            if t.last_run:
                output.append(f"  └ Last run: {t.last_run.strftime('%Y-%m-%d %H:%M:%S')}")

        return "\n".join(output)

async def delete_task(task_id: int, **kwargs) -> str:
    """
    Deletes a scheduled task by its ID.
    """
    user: Optional[User] = kwargs.get("user")
    if not user:
        return "Error: User context not found."

    scheduler = SchedulerService.get_instance()
    success = await scheduler.remove_task(task_id)

    if success:
        return f"✅ Deleted task {task_id}."
    else:
        return f"❌ Could not find task with ID {task_id}."
