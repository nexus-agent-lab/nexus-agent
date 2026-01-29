import asyncio
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlmodel import select

from app.core.db import get_session
from app.core.mq import MessageType, MQService, UnifiedMessage
from app.models.user import User

logger = logging.getLogger("nexus.worker")


class AgentWorker:
    """
    Background worker that processes incoming messages from the MQ Inbox.
    It links the MQ to the LangGraph Agent.
    """

    _running = False
    _task = None
    _agent_graph = None

    @classmethod
    def set_agent_graph(cls, graph):
        cls._agent_graph = graph

    @classmethod
    async def start(cls):
        if cls._running:
            return
        if not cls._agent_graph:
            logger.error("Cannot start AgentWorker: Agent Graph not set.")
            return

        cls._running = True
        cls._task = asyncio.create_task(cls._loop())
        logger.info("Agent Worker Started.")

    @classmethod
    async def stop(cls):
        cls._running = False
        if cls._task:
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent Worker Stopped.")

    @classmethod
    async def _resolve_user(cls, msg: UnifiedMessage) -> User:
        """Resolve Nexus User from UnifiedMessage using Identity System."""
        from app.core.auth_service import AuthService

        # 1. Try to find existing Identity binding
        user = await AuthService.get_user_by_identity(msg.channel.value, str(msg.channel_id))
        if user:
            return user

        # 2. If not bound, create a temporary/guest user context
        # This allows UNBOUND users to interact (if allowed) or just to send /bind
        # We check specific API Key pattern to reuse existing logic if possible,
        # but ideally we just strictly look up by identity.

        # For backward compatibility / auto-provisioning:
        # We can still create a "Guest" user.
        username = f"{msg.channel.value}_{msg.channel_id}"
        pseudo_key = f"{msg.channel.value}_{msg.channel_id}"

        async for session in get_session():
            # Check if we already created a guest user for this ID
            result = await session.execute(select(User).where(User.api_key == pseudo_key))
            user = result.scalars().first()
            if user:
                return user

            # Create new Guest User
            # Role = 'guest' to restrict sensitive tools until bound
            new_user = User(username=username, api_key=pseudo_key, role="guest")
            session.add(new_user)
            await session.commit()
            return new_user
        return None

    @classmethod
    async def _process_message(cls, msg: UnifiedMessage):
        """Process a message through the Agent with live updates."""
        logger.info(f"Processing Message: {msg.id} [{msg.content}]")

        # 0. Intercept Binding Command
        # /bind 123456 or 绑定 123456
        clean_content = msg.content.strip()
        if clean_content.startswith(("/bind", "绑定")):
            try:
                parts = clean_content.split()
                if len(parts) < 2:
                    raise ValueError("Missing code")
                token = parts[1]

                from app.core.auth_service import AuthService

                target_user_id = await AuthService.verify_bind_token(token)

                if target_user_id:
                    # Bind it!
                    success = await AuthService.bind_identity(
                        user_id=target_user_id,
                        provider=msg.channel.value,
                        provider_user_id=str(msg.channel_id),
                        username=msg.meta.get("username") or msg.meta.get("feishu_sender_id"),
                    )
                    reply_text = (
                        "✅ Success! Account linked."
                        if success
                        else "⚠️ This account is already linked to another user."
                    )
                else:
                    reply_text = "❌ Invalid or expired token. Generate a new one in Dashboard."
            except Exception:
                reply_text = "Usage: /bind <6-digit-code>"

            # Send immediate reply
            await MQService.push_outbox(
                UnifiedMessage(
                    channel=msg.channel,
                    channel_id=msg.channel_id,
                    content=reply_text,
                    msg_type=MessageType.TEXT,
                    meta={"reply_to": msg.id},
                )
            )
            return

        user = await cls._resolve_user(msg)
        if not user:
            return

        # Target message ID for editing (if provided by interface)
        target_msg_id = msg.meta.get("target_message_id")

        initial_state = {
            "messages": [HumanMessage(content=msg.content)],
            "user": user,
            "session_id": None,
        }

        # 1. Resolve Session & History
        # We need to do this OUTSIDE the graph to avoid duplication
        from app.core.session import SessionManager

        session = await SessionManager.get_or_create_session(user.id)
        history = await SessionManager.get_history(session.id, limit=10)

        # 2. Convert history to LangChain messages
        history_msgs = []
        for h_msg in history:
            if h_msg.type == "human":
                history_msgs.append(HumanMessage(content=h_msg.content))
            elif h_msg.type == "ai":
                history_msgs.append(AIMessage(content=h_msg.content))
            elif h_msg.type == "tool":
                history_msgs.append(
                    ToolMessage(
                        content=h_msg.content,
                        tool_call_id=h_msg.tool_call_id or "unknown",
                        name=h_msg.tool_name or "unknown",
                    )
                )

        # 3. Construct Initial State: [History] + [Current Message]
        # This ensures the Agent sees the full context immediately
        initial_state["messages"] = history_msgs + initial_state["messages"]
        initial_state["session_id"] = session.id

        current_thought = ""
        current_status = ""
        last_outbox_time = 0

        try:
            from app.core.agent import stream_agent_events

            async for event in stream_agent_events(cls._agent_graph, initial_state):
                ev_type = event["event"]
                ev_data = event["data"]

                if ev_type == "thought":
                    current_thought += ev_data
                elif ev_type == "tool_start":
                    current_status = f"🔧 **Calling Tool**: `{ev_data['name']}`..."
                elif ev_type == "tool_end":
                    current_status = f"✅ **Tool Finished**: `{ev_data['name']}`"
                elif ev_type == "final_answer":
                    # Final answer completes the cycle
                    reply = UnifiedMessage(
                        channel=msg.channel,
                        channel_id=msg.channel_id,
                        content=ev_data,
                        msg_type=MessageType.TEXT,
                        meta={"reply_to": msg.id, "target_message_id": target_msg_id},
                    )
                    await MQService.push_outbox(reply)
                    return

                # Throttle intermediate updates
                now = time.time()
                if target_msg_id and (now - last_outbox_time > 1.5):
                    # Prepare update text
                    thought_preview = current_thought[-200:] if len(current_thought) > 200 else current_thought
                    display_text = f"💭 ...{thought_preview}\n\n{current_status}" if thought_preview else current_status

                    if display_text:
                        update_msg = UnifiedMessage(
                            channel=msg.channel,
                            channel_id=msg.channel_id,
                            content=display_text,
                            msg_type=MessageType.UPDATE,
                            meta={"target_message_id": target_msg_id},
                        )
                        await MQService.push_outbox(update_msg)
                        last_outbox_time = now

        except Exception as e:
            logger.error(f"Agent Execution Failed: {e}", exc_info=True)
            error_reply = UnifiedMessage(
                channel=msg.channel,
                channel_id=msg.channel_id,
                content=f"❌ Error: {str(e)}",
                msg_type=MessageType.TEXT,
                meta={"target_message_id": target_msg_id},
            )
            await MQService.push_outbox(error_reply)
