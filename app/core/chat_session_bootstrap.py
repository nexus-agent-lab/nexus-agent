import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.core.session import SessionManager
from app.models.session import Session
from app.models.user import User

logger = logging.getLogger("nexus.chat_session")


async def build_session_state(
    *,
    user: User,
    incoming_message: str,
    thread_id: str | None,
    trace_id,
    history_limit: int = 10,
    persist_user_message: bool = True,
) -> tuple[dict, Session, bool]:
    """
    Resolve a persistent chat session and rebuild the graph input state.
    """
    session, created_new_thread = await SessionManager.resolve_session(
        user_id=user.id,
        session_uuid=thread_id,
    )

    history_summary, history_msgs_raw = await SessionManager.get_history_with_summary(session.id, limit=history_limit)
    summary_present = bool(history_summary)
    restored_human_count = sum(1 for msg in history_msgs_raw if msg.type == "human")
    restored_ai_count = sum(1 for msg in history_msgs_raw if msg.type == "ai")
    restored_tool_count = sum(1 for msg in history_msgs_raw if msg.type == "tool")

    logger.info(
        "CHAT SESSION RESTORE | user_id=%s | requested_thread_id=%s | resolved_session_id=%s | "
        "resolved_thread_id=%s | created_new_thread=%s | summary_present=%s | restored_raw_count=%s | "
        "restored_human=%s | restored_ai=%s | restored_tool=%s | incoming_preview=%s",
        user.id,
        thread_id or "-",
        session.id,
        session.session_uuid,
        created_new_thread,
        summary_present,
        len(history_msgs_raw),
        restored_human_count,
        restored_ai_count,
        restored_tool_count,
        incoming_message[:120].replace("\n", " "),
    )

    initial_messages = []
    if history_summary:
        initial_messages.append(
            SystemMessage(
                content=(
                    f"## PREVIOUS CONTEXT SUMMARY\n{history_summary}\n\n"
                    "The above is a summary of earlier conversation. Use it to maintain context."
                )
            )
        )

    for h_msg in history_msgs_raw:
        if h_msg.type == "human":
            initial_messages.append(HumanMessage(content=h_msg.content))
        elif h_msg.type == "ai":
            initial_messages.append(AIMessage(content=h_msg.content))
        elif h_msg.type == "tool":
            initial_messages.append(
                ToolMessage(
                    content=h_msg.content,
                    tool_call_id=h_msg.tool_call_id or "unknown",
                    name=h_msg.tool_name or "unknown",
                )
            )

    initial_messages.append(HumanMessage(content=incoming_message))

    if persist_user_message:
        await SessionManager.save_message(
            session_id=session.id,
            role="user",
            type="human",
            content=incoming_message,
        )

    initial_state = {
        "messages": initial_messages,
        "user": user,
        "trace_id": trace_id,
        "session_id": session.id,
    }

    return initial_state, session, created_new_thread
