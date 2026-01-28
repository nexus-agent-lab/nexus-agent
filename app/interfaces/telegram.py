import asyncio
import os
import uuid
import logging
from typing import List
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from langchain_core.messages import HumanMessage
from app.core.agent import stream_agent_events
import time

from app.models.user import User

logger = logging.getLogger("nexus.telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

# Reference to the agent graph (injected from main)
_agent_graph = None

def set_agent_graph(graph):
    global _agent_graph
    _agent_graph = graph

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from sqlmodel import select

async def get_or_create_telegram_user(tg_id: str, username: str) -> User:
    """
    Resolves a Telegram ID to an internal Nexus User.
    Uses 'tg_{id}' as the API Key for stable mapping.
    """
    pseudo_api_key = f"tg_{tg_id}"
    username = username or f"tg_user_{tg_id}"
    
    # We need a session. Since we are outside FastAPI dependency injection,
    # we manually invoke the generator.
    async for session in get_session():
        # Check existing
        result = await session.execute(select(User).where(User.api_key == pseudo_api_key))
        user = result.scalars().first()
        
        if user:
            return user
            
        # Create new
        new_user = User(
            username=username,
            api_key=pseudo_api_key,
            role="user" # Default role
        )
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        logger.info(f"Created new DB user for Telegram ID {tg_id} -> User ID {new_user.id}")
        return new_user
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🚀 Nexus Agent Online. I am ready to serve.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Send me a voice or text message to interact with your Home.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Security Check
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS and "*" not in ALLOWED_USER_IDS:
        logger.warning(f"Unauthorized access attempt from Telegram User: {user_id}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Unauthorized access.")
        return

    if not _agent_graph:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Agent system is not initialized.")
        return

    user_text = update.message.text
    
    # Notify user we are thinking
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Resolve Internal User from DB
    internal_user = await get_or_create_telegram_user(user_id, update.effective_user.username)
    
    if not internal_user:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ System Error: Could not resolve user profile.")
        return

    try:
        # Initial State
        initial_state = {
            "messages": [HumanMessage(content=user_text)],
            "user": internal_user,
            "trace_id": str(uuid.uuid4())
        }
        
        # 1. Send Initial Status Message
        status_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="🚀 **Nexus is thinking...**",
            parse_mode="Markdown"
        )
        
        current_thought = ""
        current_status = ""
        final_answer = ""
        last_edit_time = time.time()
        
        # 2. Consume Stream
        async for event in stream_agent_events(_agent_graph, initial_state):
            ev_type = event["event"]
            ev_data = event["data"]
            
            if ev_type == "thought":
                current_thought += ev_data
            elif ev_type == "tool_start":
                current_status = f"🔧 **Calling Tool**: `{ev_data['name']}`..."
            elif ev_type == "tool_end":
                current_status = f"✅ **Tool Finished**: `{ev_data['name']}`"
            elif ev_type == "final_answer":
                final_answer = ev_data
            elif ev_type == "error":
                current_status = f"❌ **Error**: `{ev_data}`"

            # 3. Throttle Edits (Max 1 per 1.0s to avoid rate limits)
            now = time.time()
            if now - last_edit_time > 1.0:
                # Format: Final thought snippet + current status
                thought_preview = current_thought[-200:] if len(current_thought) > 200 else current_thought
                display_text = f"💭 ...{thought_preview}\n\n{current_status}" if thought_preview else current_status
                
                if not display_text: display_text = "🚀 Processing..."
                
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=status_msg.message_id,
                        text=display_text,
                        parse_mode="Markdown"
                    )
                    last_edit_time = now
                except Exception:
                    pass # Ignore 'Message is not modified' errors

        # 4. Final Update
        if final_answer:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=status_msg.message_id,
                    text=final_answer,
                    parse_mode="Markdown"
                )
            except Exception:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=final_answer)
        elif current_thought:
            # If no final_answer event but we have thoughts
             await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=current_thought,
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error processing telegram message: {e}", exc_info=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ Error: {str(e)}")

async def run_telegram_bot():
    """Starts the Telegram Bot polling loop."""
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram Interface disabled.")
        return

    # Build Custom Request object with longer timeouts
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connection_pool_size=8, read_timeout=30.0, write_timeout=30.0, connect_timeout=30.0)

    builder = ApplicationBuilder().token(TELEGRAM_TOKEN).request(request)
    
    # Check for Proxy
    proxy_url = os.getenv("TELEGRAM_PROXY_URL")
    if proxy_url:
        logger.info(f"Using Telegram Proxy: {proxy_url}")
        builder = builder.proxy_url(proxy_url).get_updates_proxy_url(proxy_url)

    application = builder.build()
    
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help_command)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(message_handler)
    
    logger.info("Starting Telegram Bot Polling...")
    await application.initialize()
    await application.start()
    
    # Set global app reference for broadcast_message
    global _global_app
    _global_app = application
    
    await application.updater.start_polling()
    
    # Keep running until cancelled
    # In a real asyncio app, we might need a better lifecycle management
    # For now, we rely on the main event loop

_global_app = None

async def broadcast_message(text: str):
    """Broadcasts a message to all allowed Telegram users."""
    if not _global_app:
        logger.warning("Telegram Bot not initialized, skipping broadcast.")
        return
        
    if not ALLOWED_USER_IDS or ALLOWED_USER_IDS == [""]:
        logger.warning("No allowed users configured for broadcast.")
        return
        
    for user_id in ALLOWED_USER_IDS:
        if user_id.strip() == "*": continue # Don't broadcast to wildcard effectively (dangerous)
        try:
            await _global_app.bot.send_message(chat_id=user_id.strip(), text=text)
        except Exception as e:
            logger.error(f"Failed to broadcast to {user_id}: {e}")

