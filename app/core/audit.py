import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import engine
from app.models.audit import AuditLog

# We'll use a functional approach or class-based Context Manager.
# Using a Context Manager is cleanest for the "Pending -> Success/Failure" flow.


async def create_audit_entry(
    trace_id: uuid.UUID,
    action: str,
    user_id: Optional[int],
    tool_name: str,
    tool_args: Optional[Dict[str, Any]],
) -> int:
    """Creates initial PENDING audit log and returns its ID."""
    async with AsyncSession(engine) as session:
        log_entry = AuditLog(
            trace_id=trace_id,
            user_id=user_id,
            action=action,
            tool_name=tool_name,
            tool_args=tool_args,
            status="PENDING",  # Initial status
            created_at=datetime.utcnow(),
        )
        session.add(log_entry)
        await session.commit()
        await session.refresh(log_entry)
        return log_entry.id


async def update_audit_entry(log_id: int, status: str, duration_ms: float, error_message: Optional[str] = None):
    """Updates the existing audit log with final status."""
    async with AsyncSession(engine) as session:
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await session.execute(stmt)
        log_entry = result.scalars().first()

        if log_entry:
            log_entry.status = status
            log_entry.duration_ms = duration_ms
            log_entry.completed_at = datetime.utcnow()
            if error_message:
                log_entry.error_message = error_message

            session.add(log_entry)
            await session.commit()


class AuditInterceptor:
    def __init__(
        self,
        trace_id: uuid.UUID,
        user_id: Optional[int],
        tool_name: str,
        tool_args: Dict[str, Any],
        user_role: str = "user",
        context: str = "home",
        tool_tags: list = None,
    ):
        self.trace_id = trace_id
        self.user_id = user_id
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.user_role = user_role
        self.context = context
        self.tool_tags = tool_tags or ["tag:safe"]  # Default to safe
        self.log_id = None
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.time()

        # --- 1. Permission Check (Phase 4) ---
        from app.core.policy import PolicyMatrix

        allowed = PolicyMatrix.is_allowed(self.user_role, self.context, self.tool_tags)

        if not allowed:
            # We log the attempt before raising error
            await create_audit_entry(
                trace_id=self.trace_id,
                user_id=self.user_id,
                action="tool_denied",
                tool_name=self.tool_name,
                tool_args=self.tool_args,
            )
            raise PermissionError(
                f"Access Denied: Role '{self.user_role}' cannot use '{self.tool_name}' "
                f"(Tags: {self.tool_tags}) in context '{self.context}'"
            )

        # --- 2. Audit Logging ---
        # Create PENDING record
        self.log_id = await create_audit_entry(
            trace_id=self.trace_id,
            user_id=self.user_id,
            action="tool_execution",
            tool_name=self.tool_name,
            tool_args=self.tool_args,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        status = "SUCCESS"
        error_msg = None

        if exc_type:
            status = "FAILURE"
            error_msg = str(exc_val)

            # Proactive Admin Notification
            from app.core.auth_service import AuthService
            asyncio.create_task(
                AuthService.notify_admins(
                    f"🚨 **Tool Error Alert**\n"
                    f"Tool: `{self.tool_name}`\n"
                    f"User ID: `{self.user_id}`\n"
                    f"Error: `{error_msg}`"
                )
            )

        # Update record
        # We use asyncio.create_task to make it non-blocking if desired,
        # but for data integrity ensuring it writes before returning is safer.
        # Given "Async fire and forget" request:
        # We can spawn a background task.
        asyncio.create_task(update_audit_entry(self.log_id, status, duration, error_msg))
