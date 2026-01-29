import asyncio
import logging
import time
import uuid

from langchain_core.messages import HumanMessage
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
        """Resolve Nexus User from UnifiedMessage info."""
        # This logic mimics get_or_create_telegram_user but generic

        # 1. Generate API Key based on Channel + Channel ID
        # e.g. tg_123456, feishu_ou_xxxxx
        pseudo_key = f"{msg.channel.value}_{msg.channel_id}"
        username = f"{msg.channel.value}_user_{msg.channel_id}"

        async for session in get_session():
            result = await session.execute(select(User).where(User.api_key == pseudo_key))
            user = result.scalars().first()
            if user:
                return user

            # Create new
            new_user = User(username=username, api_key=pseudo_key, role="user")
            session.add(new_user)
            await session.commit()
            return new_user
        return None  # Should not happen

    @classmethod
    async def _loop(cls):
        logger.info("Agent Worker Loop Running...")
        while cls._running:
            try:
                # 1. Pop from Inbox
                msg = await MQService.pop_inbox()

                if msg:
                    await cls._process_message(msg)
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent Worker Error: {e}")
                await asyncio.sleep(1.0)

    @classmethod
    async def _process_message(cls, msg: UnifiedMessage):
        """Process a message through the Agent with live updates."""
        logger.info(f"Processing Message: {msg.id} [{msg.content}]")

        user = await cls._resolve_user(msg)
        if not user:
            return

        # Target message ID for editing (if provided by interface)
        target_msg_id = msg.meta.get("target_message_id")

        initial_state = {
            "messages": [HumanMessage(content=msg.content)],
            "user": user,
            "session_id": str(uuid.uuid4()),
        }

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
