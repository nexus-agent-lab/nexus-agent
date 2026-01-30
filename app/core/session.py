import json
import logging
import uuid
from typing import List, Optional

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.session import Session, SessionMessage

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages conversational sessions and message history.
    """

    @classmethod
    async def get_or_create_session(cls, user_id: int, session_uuid: Optional[str] = None) -> Session:
        """
        Get an active session or create a new one.
        If session_uuid is provided, try to find it.
        Otherwise, find the latest active session or create a new one.
        """
        async with AsyncSessionLocal() as db:
            if session_uuid:
                result = await db.execute(
                    select(Session).where(Session.session_uuid == session_uuid, Session.user_id == user_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    return session

            # If no UUID provided or not found, try to find latest active session
            # (Optional: define policy here - always new? or reuse latest?)
            # For now, let's create a NEW session if UUID not provided to avoid endless context

            new_session = Session(user_id=user_id, session_uuid=str(uuid.uuid4()), active=True, title="New Chat")
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            return new_session

    @classmethod
    async def save_message(
        cls,
        session_id: int,
        role: str,
        type: str,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        is_pruned: bool = False,
        original_content: Optional[str] = None,
    ) -> SessionMessage:
        """
        Save a message to the session history.
        """
        async with AsyncSessionLocal() as db:
            msg = SessionMessage(
                session_id=session_id,
                role=role,
                type=type,
                content=content,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                is_pruned=is_pruned,
                original_content=original_content,
                token_count=len(content) // 4,  # Allow approximation or pass from outside
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            return msg

    @classmethod
    async def get_history(cls, session_id: int, limit: int = 10) -> List[SessionMessage]:
        """
        Retrieve recent message history for context injection.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SessionMessage)
                .where(SessionMessage.session_id == session_id)
                .order_by(SessionMessage.created_at.desc())  # Newest first
                .limit(limit)
            )
            messages = result.scalars().all()
            return list(reversed(messages))  # Return oldest -> newest

    @classmethod
    async def clear_history(cls, session_id: int):
        """
        Clear all message history for a session (soft delete or full deletion).
        """
        async with AsyncSessionLocal() as db:
            # Delete all messages in this session
            result = await db.execute(
                select(SessionMessage).where(SessionMessage.session_id == session_id)
            )
            messages = result.scalars().all()
            for msg in messages:
                await db.delete(msg)
            await db.commit()
            logger.info(f"Cleared history for session {session_id}, deleted {len(messages)} messages.")

    @classmethod
    async def prune_tool_output(cls, content: str, tool_name: str) -> tuple[str, bool, Optional[str]]:
        """
        Deterministic pruning rule.
        Returns: (pruned_content, is_pruned, original_content)
        """
        # Threshold: 500 chars
        if len(content) <= 500:
            return content, False, None

        logger.info(f"Pruning output for tool {tool_name} (size: {len(content)})")

        original = content
        summary = f"[Tool Output Truncated] Original size: {len(content)} chars.\n"

        try:
            # Try to parse as JSON
            data = json.loads(content)

            if isinstance(data, list):
                summary += f"Type: List, Count: {len(data)} items.\n"
                # Extract first 3 items IDs if possible
                ids = []
                for item in data[:3]:
                    if isinstance(item, dict):
                        ids.append(str(item.get("entity_id") or item.get("id") or "item"))
                if ids:
                    summary += f"Sample IDs: {', '.join(ids)}...\n"

            elif isinstance(data, dict):
                summary += f"Type: Dict. Keys: {', '.join(list(data.keys())[:5])}...\n"

            else:
                summary += "Structure: Complex JSON.\n"

        except json.JSONDecodeError:
            summary += "Format: Text/Raw.\n"
            summary += f"Preview: {content[:100]}...\n"

        summary += "Use `python_sandbox` to process the full data if needed."

        return summary, True, original
