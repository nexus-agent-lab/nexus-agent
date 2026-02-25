import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.auth import require_admin
from app.core.db import get_session
from app.core.mq import MQService
from app.models.audit import AuditLog
from app.models.user import User

router = APIRouter(tags=["Telemetry"])
logger = logging.getLogger(__name__)


class RedisStatus(BaseModel):
    status: str
    inbox_length: int
    outbox_length: int
    dlq_length: int
    error: Optional[str] = None


class DatabaseStatus(BaseModel):
    status: str
    error: Optional[str] = None


class SystemHealth(BaseModel):
    status: str
    timestamp: datetime


@router.get("/audit", response_model=List[AuditLog])
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Retrieve audit logs (Admin only)."""
    result = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/system/health", response_model=SystemHealth)
async def get_system_health(
    current_user: User = Depends(require_admin),
):
    """Get basic system health (Admin only)."""
    return SystemHealth(status="ok", timestamp=datetime.utcnow())


@router.get("/system/redis", response_model=RedisStatus)
async def get_redis_status(
    current_user: User = Depends(require_admin),
):
    """Get Redis queue statistics (Admin only)."""
    try:
        r = await MQService.get_redis()
        inbox_len = await r.llen(MQService.INBOX_KEY)
        outbox_len = await r.llen(MQService.OUTBOX_KEY)
        dlq_len = await r.llen(MQService.DLQ_KEY)
        return RedisStatus(status="connected", inbox_length=inbox_len, outbox_length=outbox_len, dlq_length=dlq_len)
    except Exception as e:
        logger.error(f"Redis status check failed: {e}")
        return RedisStatus(status="error", inbox_length=0, outbox_length=0, dlq_length=0, error=str(e))


@router.get("/system/database", response_model=DatabaseStatus)
async def get_database_status(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Get Database connection status (Admin only)."""
    try:
        await session.execute(text("SELECT 1"))
        return DatabaseStatus(status="connected")
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return DatabaseStatus(status="error", error=str(e))
