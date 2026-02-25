from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.memory import Memory
from app.models.user import User

router = APIRouter(prefix="/memories", tags=["memories"])


class MemoryResponse(BaseModel):
    id: int
    user_id: int
    content: str
    memory_type: str
    skill_id: Optional[int]
    created_at: datetime


class MemoryStats(BaseModel):
    total_memories: int
    memories_by_type: Dict[str, int]


@router.get("", response_model=List[MemoryResponse])
async def get_memories(
    user_id: Optional[int] = None,
    memory_type: Optional[str] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Fetch memories. Standard users can only view their own. Admins can view all.
    """
    if user_id is not None:
        if current_user.role != "admin" and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access these memories")
    else:
        if current_user.role != "admin":
            user_id = current_user.id

    query = select(Memory)

    if user_id is not None:
        query = query.where(Memory.user_id == user_id)

    if memory_type is not None:
        query = query.where(Memory.memory_type == memory_type)

    query = query.order_by(Memory.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    memories = result.scalars().all()

    return memories


@router.get("/stats", response_model=MemoryStats)
async def get_memory_stats(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get memory statistics. Standard users can only view their own stats.
    """
    if user_id is not None:
        if current_user.role != "admin" and user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access these stats")
    else:
        if current_user.role != "admin":
            user_id = current_user.id

    # Count total memories
    query_total = select(func.count(Memory.id))
    if user_id is not None:
        query_total = query_total.where(Memory.user_id == user_id)

    result_total = await session.execute(query_total)
    total = result_total.scalar_one_or_none() or 0

    # Count by type
    query_type = select(Memory.memory_type, func.count(Memory.id)).group_by(Memory.memory_type)
    if user_id is not None:
        query_type = query_type.where(Memory.user_id == user_id)

    result_type = await session.execute(query_type)
    by_type = {row[0]: row[1] for row in result_type.all()}

    return MemoryStats(total_memories=total, memories_by_type=by_type)
