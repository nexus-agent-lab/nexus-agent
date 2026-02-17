import logging
import os

from fastapi import APIRouter, Body, HTTPException, Query

from app.core.logging_config import log_buffer

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get("/log")
async def get_logs(limit: int = Query(100, ge=1, le=1000)):
    """Get recent logs from memory buffer."""
    # Convert deque to list and slice last N
    logs = list(log_buffer)[-limit:]
    # Return as plain text list or joined string? Dashboard likely expects list or string.
    # Dashboard uses st.code(resp.text), so maybe just raw text?
    # But usually APIs return JSON. Let's return JSON list.
    # If dashboard expects text, it might need adjustment involving .json()
    return {"logs": logs}


@router.post("/config")
async def update_config(key: str = Body(...), value: str = Body(...)):
    """Update runtime configuration (env vars mostly)."""
    # Allowed keys for safety
    ALLOWED_KEYS = {"DEBUG_WIRE_LOG", "LOG_LEVEL"}

    if key not in ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail=f"Key {key} not allowed. Allowed: {ALLOWED_KEYS}")

    # Update os.environ so agent.py sees it
    os.environ[key] = value
    logger.info(f"Admin updated config: {key} = {value}")
    return {"status": "updated", "key": key, "value": value}
