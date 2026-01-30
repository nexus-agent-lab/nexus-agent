import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import select

from app.core.db import AsyncSessionLocal
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage
from app.models.scheduler import ScheduledTask

logger = logging.getLogger("nexus.scheduler")

class SchedulerService:
    _instance = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerService, cls).__new__(cls)
            cls._instance._scheduler = AsyncIOScheduler()
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = SchedulerService()
        return cls._instance

    async def start(self):
        """Starts the scheduler and loads existing tasks from DB."""
        if self._scheduler.running:
            return

        logger.info("Starting Scheduler Service...")
        await self._load_tasks()
        self._scheduler.start()

    async def stop(self):
        """Stops the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler Service stopped.")

    async def _load_tasks(self):
        """Loads all enabled tasks from DB into the scheduler."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ScheduledTask).where(ScheduledTask.enabled == True))  # noqa: E712
            tasks = result.scalars().all()

            for task in tasks:
                self._add_task_to_scheduler(task)

            logger.info(f"Loaded {len(tasks)} scheduled tasks from database.")

    def _add_task_to_scheduler(self, task: ScheduledTask):
        """Adds a single task to the APScheduler instance."""
        job_id = f"task_{task.id}"

        # Remove existing job if any
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        try:
            self._scheduler.add_job(
                self._trigger_task,
                CronTrigger.from_crontab(task.cron_expr),
                id=job_id,
                args=[task.id],
                replace_existing=True
            )
        except Exception as e:
            logger.error(f"Failed to schedule task {task.id}: {e}")

    async def _trigger_task(self, task_id: int):
        """Executed when a cron job fires."""
        async with AsyncSessionLocal() as session:
            task = await session.get(ScheduledTask, task_id)
            if not task or not task.enabled:
                return

            logger.info(f"Triggering Scheduled Task: {task.description} (ID: {task.id})")

            # Create a UnifiedMessage for the agent
            # This simulates a message coming from the user or system
            msg = UnifiedMessage(
                channel=ChannelType(task.channel),
                channel_id=task.channel_id,
                user_id=str(task.user_id),
                content=task.payload.get("prompt", task.description),
                msg_type=MessageType.SYSTEM if task.task_type == "notification" else MessageType.TEXT,
                meta={
                    "triggered_by": "scheduler",
                    "task_id": task.id,
                    "is_automated": True
                }
            )

            # Push to MQ Inbox
            await MQService.push_inbox(msg)

            # Update last run time
            task.last_run = datetime.utcnow()
            session.add(task)
            await session.commit()

    async def add_task(self, task: ScheduledTask):
        """Adds a new task to DB and scheduler."""
        async with AsyncSessionLocal() as session:
            session.add(task)
            await session.commit()
            await session.refresh(task)
            self._add_task_to_scheduler(task)
            return task

    async def remove_task(self, task_id: int):
        """Removes a task from DB and scheduler."""
        async with AsyncSessionLocal() as session:
            task = await session.get(ScheduledTask, task_id)
            if task:
                await session.delete(task)
                await session.commit()

                job_id = f"task_{task_id}"
                if self._scheduler.get_job(job_id):
                    self._scheduler.remove_job(job_id)
                return True
        return False

    async def toggle_task(self, task_id: int, enabled: bool):
        """Enables or disables a task."""
        async with AsyncSessionLocal() as session:
            task = await session.get(ScheduledTask, task_id)
            if task:
                task.enabled = enabled
                session.add(task)
                await session.commit()

                if enabled:
                    self._add_task_to_scheduler(task)
                else:
                    job_id = f"task_{task_id}"
                    if self._scheduler.get_job(job_id):
                        self._scheduler.remove_job(job_id)
                return True
        return False
