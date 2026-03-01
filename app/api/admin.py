import logging
import os

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import select

from app.core.auth import require_admin
from app.core.db import AsyncSessionLocal
from app.core.logging_config import log_buffer
from app.models.llm_trace import LLMTrace
from app.models.settings import SystemSetting

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get("/log", dependencies=[Depends(require_admin)])
async def get_logs(limit: int = Query(100, ge=1, le=1000)):
    """Get recent logs from memory buffer."""
    # Convert deque to list and slice last N
    logs = list(log_buffer)[-limit:]
    # Return as plain text list or joined string? Dashboard likely expects list or string.
    # Dashboard uses st.code(resp.text), so maybe just raw text?
    # But usually APIs return JSON. Let's return JSON list.
    # If dashboard expects text, it might need adjustment involving .json()
    return {"logs": logs}


@router.post("/config", dependencies=[Depends(require_admin)])
async def update_config(key: str = Body(...), value: str = Body(...)):
    """Update runtime configuration (env vars mostly)."""
    # Allowed keys for safety
    ALLOWED_KEYS = {"DEBUG_WIRE_LOG", "LOG_LEVEL"}

    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Key {key} not allowed. Allowed: {ALLOWED_KEYS}")

    # Update os.environ so agent.py sees it
    os.environ[key] = value

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = SystemSetting(key=key, value=value)
            session.add(setting)
        await session.commit()

    logger.info(f"Admin updated config: {key} = {value}")
    return {"status": "updated", "key": key, "value": value}


@router.get("/config", dependencies=[Depends(require_admin)])
async def get_config(key: str = Query(...)):
    """Get runtime configuration (env vars mostly)."""
    ALLOWED_KEYS = {"DEBUG_WIRE_LOG", "LOG_LEVEL"}
    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Key {key} not allowed. Allowed: {ALLOWED_KEYS}")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            value = setting.value
        else:
            value = os.environ.get(key, "false")

    return {"key": key, "value": value}


@router.get("/traces", dependencies=[Depends(require_admin)])
async def get_traces(limit: int = Query(50, ge=1, le=1000)):
    """Get recent LLM call logs."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(LLMTrace).order_by(LLMTrace.created_at.desc()).limit(limit))
        traces = result.scalars().all()

    return {"traces": traces}


@router.get("/traces/grouped", dependencies=[Depends(require_admin)])
async def get_grouped_traces(limit: int = Query(50, ge=1, le=1000)):
    """Get LLM traces grouped by trace_id."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(
                LLMTrace.trace_id,
                LLMTrace.session_id,
                LLMTrace.user_id,
                func.sum(LLMTrace.latency_ms).label("total_latency_ms"),
                func.count(LLMTrace.id).label("call_count"),
                func.max(LLMTrace.created_at).label("created_at"),
            )
            .group_by(LLMTrace.trace_id, LLMTrace.session_id, LLMTrace.user_id)
            .order_by(func.max(LLMTrace.created_at).desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        rows = result.all()

        grouped_traces = []
        for row in rows:
            # Fetch all traces for this trace_id to include as children
            child_stmt = select(LLMTrace).where(LLMTrace.trace_id == row.trace_id).order_by(LLMTrace.created_at.asc())
            child_result = await session.execute(child_stmt)
            children = child_result.scalars().all()

            grouped_traces.append(
                {
                    "trace_id": row.trace_id,
                    "session_id": row.session_id,
                    "user_id": row.user_id,
                    "total_latency_ms": row.total_latency_ms,
                    "call_count": row.call_count,
                    "created_at": row.created_at,
                    "steps": children,
                }
            )

    return {"traces": grouped_traces}


@router.post("/mcp/reload", dependencies=[Depends(require_admin)])
async def reload_mcp():
    """Reload MCP servers."""
    from app.core.mcp_manager import MCPManager

    manager = MCPManager.get_instance()
    await manager.reload()
    return {"status": "success", "message": "MCP servers reloaded successfully."}
