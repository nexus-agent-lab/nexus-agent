import logging
from typing import Optional

from langchain_core.tools import tool

from app.core.db import AsyncSessionLocal
from app.core.decorators import require_role
from app.models.watch_rule import WatchRule

logger = logging.getLogger(__name__)


@tool
@require_role("user")
async def watch_entity(
    entity_id: str,
    condition: str,
    action: str = "notify",
    message: Optional[str] = None,
    cooldown_minutes: int = 60,
    **kwargs,
) -> str:
    """
    Sets up a proactive watch rule for a Home Assistant entity.
    - entity_id: The HA entity ID (e.g. 'sensor.phone_battery')
    - condition: A python-like comparison (e.g. '< 2' or "== 'on'")
    - action: What to do ('notify' is default)
    - message: Optional custom notification message
    - cooldown_minutes: Frequency limit for this rule
    """
    user_id = kwargs.get("user_id")
    if not user_id:
        return "Error: user_id is required to set up a watch rule."

    async with AsyncSessionLocal() as session:
        rule = WatchRule(
            user_id=user_id,
            entity_pattern=entity_id,
            condition=condition,
            action=action,
            payload={"message": message} if message else {},
            cooldown_minutes=cooldown_minutes,
        )
        session.add(rule)
        await session.commit()

    return f"✅ Proactive watch established for `{entity_id}` when `{condition}`. Action: {action}."


@tool
@require_role("user")
async def list_watch_rules(**kwargs) -> str:
    """Lists all active proactive watch rules for the current user."""
    user_id = kwargs.get("user_id")
    if not user_id:
        return "Error: user_id is required."

    from sqlmodel import select

    async with AsyncSessionLocal() as session:
        statement = select(WatchRule).where(WatchRule.user_id == user_id)
        results = await session.execute(statement)
        rules = results.scalars().all()

    if not rules:
        return "You have no active watch rules."

    out = ["Your Watch Rules:"]
    for r in rules:
        status = "Active" if r.is_active else "Paused"
        out.append(f"- ID {r.id}: `{r.entity_pattern}` {r.condition} -> {r.action} ({status})")

    return "\n".join(out)
