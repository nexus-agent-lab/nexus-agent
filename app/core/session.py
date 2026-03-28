import json
import logging
import uuid
from typing import List, Optional

from sqlalchemy import func, select

from app.core.db import AsyncSessionLocal
from app.core.llm_utils import ainvoke_with_backoff, count_text_tokens, get_llm_client
from app.models.session import Session, SessionMessage, SessionSummary
from app.tools.session_workspace import delete_session_workspace

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
    async def resolve_session(cls, user_id: int, session_uuid: Optional[str] = None) -> tuple[Session, bool]:
        """
        Resolve a session and report whether a new one had to be created.
        """
        async with AsyncSessionLocal() as db:
            if session_uuid:
                result = await db.execute(
                    select(Session).where(Session.session_uuid == session_uuid, Session.user_id == user_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    return session, False

                logger.warning(
                    "CHAT SESSION MISS | user_id=%s | requested_thread_id=%s | action=create_new_session",
                    user_id,
                    session_uuid,
                )

            new_session = Session(user_id=user_id, session_uuid=str(uuid.uuid4()), active=True, title="New Chat")
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)
            return new_session, True

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
                token_count=count_text_tokens(content)[0],
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
        Clear all persisted conversation history for a session, including summaries
        and any materialized workspace artifacts associated with that session.
        """
        session_user_id: Optional[int] = None
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, session_id)
            if session:
                session_user_id = session.user_id

            result = await db.execute(select(SessionMessage).where(SessionMessage.session_id == session_id))
            messages = result.scalars().all()
            for msg in messages:
                await db.delete(msg)

            summary_result = await db.execute(select(SessionSummary).where(SessionSummary.session_id == session_id))
            summaries = summary_result.scalars().all()
            for summary in summaries:
                await db.delete(summary)

            await db.commit()

        workspace_deleted = False
        if session_user_id is not None:
            try:
                workspace_deleted = delete_session_workspace(session_user_id, session_id)
            except FileNotFoundError:
                workspace_deleted = False
            except Exception as e:
                logger.warning("Failed to delete session workspace | session_id=%s | error=%s", session_id, e)

        logger.info(
            "Cleared history for session %s, deleted %s messages, %s summaries, workspace_deleted=%s.",
            session_id,
            len(messages),
            len(summaries),
            workspace_deleted,
        )

    @classmethod
    async def prune_tool_output(cls, content: str, tool_name: str) -> tuple[str, bool, Optional[str]]:
        """
        Deterministic pruning rule.
        Returns: (pruned_content, is_pruned, original_content)
        """
        # Threshold: 2000 chars (Raised from 500 to allow small structured data like HA sensor lists)
        if len(content) <= 2000:
            return content, False, None

        logger.info(f"Pruning output for tool {tool_name} (size: {len(content)})")

        original = content
        summary = f"[Tool Output Truncated] Original size: {len(content)} chars.\n"

        try:
            # Try to parse as JSON
            data = json.loads(content)

            if isinstance(data, list):
                summary += f"Type: List, Count: {len(data)} items.\n"
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

        if tool_name.startswith("browser_"):
            summary += "Prefer narrowing the page query or extracting only the relevant section before continuing."
        else:
            summary += "Use a narrower follow-up step or a structure-aware tool before processing the full data."

        return summary, True, original

    # =========================================
    # AUTO-COMPACTING (P0.5)
    # =========================================

    @classmethod
    async def maybe_compact(cls, session_id: int, threshold: int = 20, keep_last: int = 15):
        """
        Conditionally trigger compaction only if meaningful history has accumulated.
        Reduces unnecessary LLM calls (Optimization for GLM Flash).
        """
        try:
            async with AsyncSessionLocal() as db:
                # Count unarchived messages
                stmt = select(func.count(SessionMessage.id)).where(
                    SessionMessage.session_id == session_id,
                    SessionMessage.is_archived == False,  # noqa: E712
                )
                result = await db.execute(stmt)
                count = result.scalar_one()

                if count > threshold:
                    logger.info(
                        f"Session {session_id} has {count} unarchived messages (threshold {threshold}). Triggering compaction."
                    )
                    await cls.compact_session(session_id, keep_last=keep_last)
                else:
                    # debugging noise reduction
                    # logger.debug(f"Session {session_id} count {count} < {threshold}. Skipping compaction.")
                    pass
        except Exception as e:
            logger.error(f"Error in maybe_compact for session {session_id}: {e}")

    @classmethod
    async def compact_session(cls, session_id: int, keep_last: int = 15):
        """
        Background task: Compact old messages into a summary.
        Keeps the last `keep_last` messages raw, archives the rest.
        """
        try:
            from app.models.session import SessionSummary

            async with AsyncSessionLocal() as db:
                # 1. Count unarchived messages
                count_stmt = select(func.count()).where(
                    SessionMessage.session_id == session_id,
                    SessionMessage.is_archived == False,  # noqa: E712
                )
                result = await db.execute(count_stmt)
                count = result.scalar()

                if count <= keep_last:
                    return  # No need to compact

                # 2. Fetch older messages to archive
                limit = count - keep_last
                msgs_stmt = (
                    select(SessionMessage)
                    .where(SessionMessage.session_id == session_id, SessionMessage.is_archived == False)  # noqa: E712
                    .order_by(SessionMessage.created_at.asc())
                    .limit(limit)
                )
                result = await db.execute(msgs_stmt)
                to_archive = result.scalars().all()

                if not to_archive:
                    return

                # 3. Generate Summary using LLM
                llm = get_llm_client()

                # Format context for summarization
                context_lines = []
                for m in to_archive:
                    role_str = m.role.upper()
                    if m.role == "tool":
                        role_str = f"TOOL ({m.tool_name})"
                    content_snippet = m.content[:500] + "..." if len(m.content) > 500 else m.content
                    context_lines.append(f"{role_str}: {content_snippet}")

                context_text = "\n".join(context_lines)

                prompt = (
                    f"Summarize the following conversation history into a concise, factual paragraph. "
                    f"Focus on key decisions, facts, user preferences, and outcomes. "
                    f"Ignore improved greetings or small talk.\n\n"
                    f"History:\n{context_text}\n\n"
                    f"Summary:"
                )

                response = await ainvoke_with_backoff(llm, prompt, operation_name="session.compact")
                summary_text = response.content.strip()

                # 4. Save SessionSummary
                start_msg_id = to_archive[0].id
                end_msg_id = to_archive[-1].id

                new_summary = SessionSummary(
                    session_id=session_id,
                    summary=summary_text,
                    start_msg_id=start_msg_id,
                    end_msg_id=end_msg_id,
                    msg_count=len(to_archive),
                )
                db.add(new_summary)

                # 5. Mark messages as archived
                for msg in to_archive:
                    msg.is_archived = True

                await db.commit()
                logger.info(f" compacted {len(to_archive)} messages into summary for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to compact session {session_id}: {e}")

    @classmethod
    async def get_unarchived_message_count(cls, session_id: int) -> int:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.count()).where(
                    SessionMessage.session_id == session_id,
                    SessionMessage.is_archived == False,  # noqa: E712
                )
            )
            return int(result.scalar() or 0)

    @classmethod
    async def compact_for_token_budget(
        cls,
        session_id: int,
        *,
        estimated_input_tokens: int,
        target_tokens: int,
        min_keep_last: int = 6,
        max_keep_last: int = 15,
    ) -> bool:
        """
        Compact persisted history only when the current estimated prompt size is above
        the soft limit and there is enough unarchived history to make compaction useful.
        """
        count = await cls.get_unarchived_message_count(session_id)
        if count <= max_keep_last:
            return False

        overflow_ratio = max(0.0, (estimated_input_tokens - target_tokens) / max(1, estimated_input_tokens))
        keep_last = max(min_keep_last, min(max_keep_last, int(max_keep_last - (overflow_ratio * max_keep_last))))
        keep_last = max(min_keep_last, min(keep_last, count - 1))
        if count <= keep_last:
            return False

        logger.info(
            "Token-aware compact trigger | session_id=%s | unarchived=%s | estimated_tokens=%s | target_tokens=%s | keep_last=%s",
            session_id,
            count,
            estimated_input_tokens,
            target_tokens,
            keep_last,
        )
        await cls.compact_session(session_id, keep_last=keep_last)
        return True

    @classmethod
    async def get_history_with_summary(cls, session_id: int, limit: int = 15) -> tuple[str, List[SessionMessage]]:
        """
        Retrieve context: (Summary of old messages, List of recent raw messages).
        """
        from app.models.session import SessionSummary

        async with AsyncSessionLocal() as db:
            # 1. Get all summaries (oldest to newest)
            result = await db.execute(
                select(SessionSummary.summary)
                .where(SessionSummary.session_id == session_id)
                .order_by(SessionSummary.created_at.asc())
            )
            summaries = result.scalars().all()
            full_summary = "\n\n".join(summaries) if summaries else ""

            # 2. Get recent unarchived messages
            result = await db.execute(
                select(SessionMessage)
                .where(SessionMessage.session_id == session_id, SessionMessage.is_archived == False)  # noqa: E712
                .order_by(SessionMessage.created_at.desc())  # Newest first
                .limit(limit)
            )
            messages = list(reversed(result.scalars().all()))  # Return oldest -> newest

            return full_summary, messages
