from langchain_core.tools import tool
from sqlmodel import select

from app.core.db import AsyncSessionLocal
from app.core.decorators import require_role, with_user
from app.models.product import ProductSuggestion
from app.models.user import User


@tool
@with_user()
async def submit_suggestion(content: str, category: str = "feature", user: User = None, **kwargs) -> str:
    """
    Submits a new product suggestion, feature request, or bug report.
    - content: The details of the suggestion
    - category: 'feature', 'bug', or 'improvement'
    """
    # Decorator injects 'user_object' into kwargs
    user = user or kwargs.get("user_object")
    if not user:
        return "Error: User context required."

    async with AsyncSessionLocal() as session:
        suggestion = ProductSuggestion(user_id=user.id, content=content, category=category, status="pending")
        session.add(suggestion)
        await session.commit()
        await session.refresh(suggestion)

    return f"✅ Suggestion #{suggestion.id} submitted successfully! We've added it to the roadmap."


@tool
@require_role("admin")
async def list_suggestions(status: str = "pending", limit: int = 10, **kwargs) -> str:
    """
    (Admin Only) Lists product suggestions filtered by status.
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ProductSuggestion)
            .where(ProductSuggestion.status == status)
            .order_by(ProductSuggestion.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        suggestions = result.scalars().all()

    if not suggestions:
        return f"No {status} suggestions found."

    lines = [f"**{status.upper()} Suggestions:**"]
    for s in suggestions:
        lines.append(f"- [#{s.id}] {s.content} (Cat: {s.category}, Votes: {s.votes})")

    return "\n".join(lines)


@tool
@require_role("admin")
async def update_suggestion_status(suggestion_id: int, status: str, **kwargs) -> str:
    """
    (Admin Only) Updates the status of a suggestion (e.g., 'approved', 'rejected', 'implemented').
    """
    valid_statuses = ["pending", "approved", "rejected", "implemented"]
    if status not in valid_statuses:
        return f"Error: Invalid status. Must be one of {valid_statuses}"

    async with AsyncSessionLocal() as session:
        suggestion = await session.get(ProductSuggestion, suggestion_id)
        if not suggestion:
            return f"Error: Suggestion #{suggestion_id} not found."

        suggestion.status = status
        session.add(suggestion)
        await session.commit()

    return f"✅ Suggestion #{suggestion_id} updated to '{status}'."
