import asyncio
import logging
import time

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlmodel import select

from app.core.db import get_session
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage
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
    _tools = []

    @classmethod
    def set_agent_graph(cls, graph):
        cls._agent_graph = graph

    @classmethod
    def set_tools(cls, tools: list):
        cls._tools = tools

    @classmethod
    def get_tools(cls) -> list:
        return cls._tools

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
        # Determine the most specific provider ID available
        provider_id = str(msg.channel_id)
        if msg.channel == ChannelType.TELEGRAM and "telegram_user_id" in msg.meta:
            provider_id = str(msg.meta["telegram_user_id"])
        elif msg.channel == ChannelType.FEISHU and "feishu_sender_id" in msg.meta:
            provider_id = str(msg.meta["feishu_sender_id"])

        user = await AuthService.get_user_by_identity(msg.channel.value, provider_id)
        role = user.role if user else "N/A"
        uid = user.id if user else "N/A"
        logger.info(
            f"[DEBUG] _resolve_user: channel={msg.channel.value}, provider_id={provider_id}, user_found={user is not None}, user_id={uid}, role={role}"
        )
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
    async def _loop(cls):
        """Main processing loop."""
        logger.info("Agent Worker Loop Started.")
        while cls._running:
            try:
                msg = await MQService.pop_inbox()
                if msg:
                    # Process each message in a separate task
                    # to handle concurrency effectively
                    asyncio.create_task(cls._process_message(msg))
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Error in AgentWorker loop: {e}", exc_info=True)
                await asyncio.sleep(1)

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
                    # Determine the most specific provider ID for binding
                    provider_id = str(msg.channel_id)
                    if msg.channel == ChannelType.TELEGRAM and "telegram_user_id" in msg.meta:
                        provider_id = str(msg.meta["telegram_user_id"])
                    elif msg.channel == ChannelType.FEISHU and "feishu_sender_id" in msg.meta:
                        provider_id = str(msg.meta["feishu_sender_id"])

                    logger.info(f"Worker attempting to bind {msg.channel} ID {provider_id} to User {target_user_id}")
                    result = await AuthService.bind_identity(
                        user_id=target_user_id,
                        provider=msg.channel.value,
                        provider_user_id=provider_id,
                        username=msg.meta.get("username")
                        or msg.meta.get("feishu_sender_id")
                        or msg.meta.get("telegram_username"),
                    )

                    from app.core.auth_service import BindResult
                    from app.core.i18n import get_text

                    # Determine language (best effort, target_user might have preference)
                    # We can fetch target user language
                    target_lang = "en"
                    # fetch user again to get lang? or just assume EN or use system.
                    # Ideally we use the user's language if available.
                    from app.core.db import AsyncSessionLocal

                    async with AsyncSessionLocal() as session:
                        u = await session.get(User, target_user_id)
                        if u and u.language:
                            target_lang = u.language

                    meta_extras = {}
                    reply_text = get_text("bind_fail", target_lang)

                    if result == BindResult.SUCCESS:
                        reply_text = get_text("bind_success", target_lang, user_id=target_user_id)
                        # Fetch Allowed Tools to update Menu
                        # ... (existing logic) ...
                    elif result == BindResult.PROVIDER_CONFLICT:
                        reply_text = get_text("bind_conflict_provider", target_lang)
                    elif result == BindResult.USER_CONFLICT:
                        reply_text = get_text("bind_conflict_user", target_lang)

                    if result == BindResult.SUCCESS:
                        # Fetch Allowed Tools to update Menu
                        from app.core.db import AsyncSessionLocal

                        async with AsyncSessionLocal() as session:
                            u = await session.get(User, target_user_id)
                            if u:
                                allowed_tools = AuthService.get_allowed_tools(u, cls._tools)
                                # Map to commands
                                commands = []
                                for t in allowed_tools:
                                    t_name = getattr(t, "name", str(t))
                                    t_desc = getattr(t, "description", "")
                                    cmd = t_name.lower().replace("_", "")[:30]
                                    desc = t_desc[:100] if t_desc else "Execute tool"
                                    commands.append({"command": cmd, "description": desc})

                                commands.insert(0, {"command": "start", "description": "Start Nexus"})
                                commands.insert(1, {"command": "help", "description": "Show Help"})
                                commands.insert(2, {"command": "bind", "description": "Link Account"})
                                commands.insert(3, {"command": "reset", "description": "Reset Session"})
                                meta_extras["telegram_commands"] = commands

                else:
                    reply_text = "❌ Invalid or expired token. Generate a new one in Dashboard."
                    meta_extras = {}
            except Exception:
                reply_text = "Usage: /bind <6-digit-code>"
                meta_extras = {}

            # Send immediate reply
            await MQService.push_outbox(
                UnifiedMessage(
                    channel=msg.channel,
                    channel_id=msg.channel_id,
                    content=reply_text,
                    msg_type=MessageType.TEXT,
                    meta={"reply_to": msg.id, **meta_extras},
                )
            )
            return

        user = await cls._resolve_user(msg)
        if not user:
            return

        # 1. Onboarding Check for Guest Users
        if user.role == "guest":
            from app.core.i18n import get_text, resolve_language

            # Resolve language: User preference (if any) -> Message Content -> Default
            guest_lang = resolve_language(user, msg.content)
            onboarding_text = get_text("welcome_guest", guest_lang)

            await MQService.push_outbox(
                UnifiedMessage(
                    channel=msg.channel,
                    channel_id=msg.channel_id,
                    content=onboarding_text,
                    msg_type=MessageType.TEXT,
                    meta={"reply_to": msg.id},
                )
            )
            return

        # Target message ID for editing (if provided by interface)
        target_msg_id = msg.meta.get("target_message_id")

        initial_state = {
            "messages": [HumanMessage(content=msg.content)],
            "user": user,  # Enforce policies
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
        tool_history = []  # Track recent tools for status board
        last_outbox_time = 0

        try:
            from app.core.agent import stream_agent_events

            async for event in stream_agent_events(cls._agent_graph, initial_state):
                ev_type = event["event"]
                ev_data = event["data"]

                if ev_type == "thought":
                    current_thought += ev_data
                elif ev_type == "tool_start":
                    # Extract and format arguments for preview
                    args = ev_data.get("args", {})
                    args_preview = ""
                    if args:
                        # Show first few args concisely
                        arg_items = list(args.items())[:2]  # First 2 args
                        args_str = ", ".join([f"{k}={str(v)[:30]}" for k, v in arg_items])
                        if len(args) > 2:
                            args_str += "..."
                        args_preview = f" ({args_str})"

                    current_status = f"🔧 **Running**: `{ev_data['name']}`{args_preview}"
                    tool_history.append(f"⚙️ {ev_data['name']}")

                    # Proactively send typing status on tool start
                    await MQService.push_outbox(
                        UnifiedMessage(
                            channel=msg.channel,
                            channel_id=msg.channel_id,
                            content="typing",
                            msg_type=MessageType.ACTION,
                        )
                    )

                elif ev_type == "tool_end":
                    result_preview = ev_data.get("result", "")[:100]
                    current_status = f"✅ **Completed**: `{ev_data['name']}`"
                    if result_preview:
                        current_status += f"\n   └─ _{result_preview}_"

                elif ev_type == "final_answer":
                    # Final answer completes the cycle
                    reply = UnifiedMessage(
                        channel=msg.channel,
                        channel_id=msg.channel_id,
                        content=ev_data,
                        msg_type=MessageType.TEXT,
                        meta={
                            "reply_to": msg.id,
                        },
                    )
                    # If we had a pinned message (other platforms), unpin it
                    if target_msg_id:
                        reply.meta["unpin_message_id"] = target_msg_id

                    await MQService.push_outbox(reply)
                    return

                # Throttle intermediate updates
                now = time.time()
                if now - last_outbox_time > 3.0:
                    # Always send typing status periodically (Telegram)
                    if msg.channel == ChannelType.TELEGRAM:
                        await MQService.push_outbox(
                            UnifiedMessage(
                                channel=msg.channel,
                                channel_id=msg.channel_id,
                                content="typing",
                                msg_type=MessageType.ACTION,
                            )
                        )

                    # Update board if target_msg_id present (for Feishu/Web if they use board)
                    elif target_msg_id:
                        # Prepare enhanced status board
                        sections = []
                        sections.append("🤖 **Nexus Agent Working...**")

                        if tool_history:
                            recent_tools = tool_history[-3:]
                            sections.append("\\n**Recent Activity:**")
                            sections.append("\\n".join(recent_tools))

                        if current_status:
                            sections.append(f"\\n{current_status}")

                        if current_thought and len(current_thought) > 50:
                            thought_preview = current_thought[-150:].strip()
                            sections.append(f"\\n💭 _{thought_preview}_")

                        display_text = "\\n".join(sections)

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
