import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.product import ProductSuggestion
from app.models.user import User

router = APIRouter(prefix="/roadmap", tags=["Roadmap"])
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[ProductSuggestion])
async def list_suggestions(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all product suggestions with filters."""
    query = select(ProductSuggestion)
    if status:
        query = query.where(ProductSuggestion.status == status.lower())
    if category:
        query = query.where(ProductSuggestion.category == category.lower())

    query = query.order_by(desc(ProductSuggestion.created_at)).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/{suggestion_id}/status")
async def update_suggestion_status(
    suggestion_id: int,
    new_status: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update the status of a suggestion (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update roadmap status")

    suggestion = await session.get(ProductSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    valid_statuses = ["pending", "approved", "implemented", "rejected"]
    if new_status.lower() not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    suggestion.status = new_status.lower()
    session.add(suggestion)
    await session.commit()
    return {"message": f"Suggestion {suggestion_id} updated to {new_status}"}


@router.delete("/{suggestion_id}")
async def delete_suggestion(
    suggestion_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a suggestion (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete suggestions")

    suggestion = await session.get(ProductSuggestion, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    await session.delete(suggestion)
    await session.commit()
    return {"message": "Suggestion deleted"}
