import asyncio
import os
import uuid
import logging
from typing import List
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from langchain_core.messages import HumanMessage

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
        # Invoke Agent
        initial_state = {
            "messages": [HumanMessage(content=user_text)],
            "user": internal_user,
            "trace_id": str(uuid.uuid4()) # Must be valid UUID for AuditLog
        }
        
        final_state = await _agent_graph.ainvoke(initial_state)
        response_text = final_state["messages"][-1].content
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response_text)
        
    except Exception as e:
        logger.error(f"Error processing telegram message: {e}")
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
    await application.updater.start_polling()
    
    # Keep running until cancelled
    # In a real asyncio app, we might need a better lifecycle management
    # For now, we rely on the main event loop
