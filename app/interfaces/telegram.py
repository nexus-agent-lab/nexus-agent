import logging
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app.core.dispatcher import InterfaceDispatcher
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage

logger = logging.getLogger("nexus.telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

# Global reference to Telegram Application (for outbound sending)
_telegram_app = None


# ==========================================
# Outbound Handler (Consumer)
# ==========================================


async def send_telegram_message(msg: UnifiedMessage):
    """
    Handler registered with Dispatcher to send messages via Telegram.
    Supports both sending new messages and editing existing ones.
    """
    if not _telegram_app:
        logger.warning("Telegram App not initialized, cannot send message.")
        return

    chat_id = msg.channel_id
    text = msg.content
    target_msg_id = msg.meta.get("target_message_id")

    try:
        if msg.msg_type == MessageType.UPDATE and target_msg_id:
            # Edit existing status message
            await _telegram_app.bot.edit_message_text(
                chat_id=chat_id, message_id=int(target_msg_id), text=text, parse_mode="Markdown"
            )
        else:
            # Send new message (or final replacement)
            if target_msg_id:
                # If we have a target, try to edit it first for the final response
                try:
                    await _telegram_app.bot.edit_message_text(
                        chat_id=chat_id, message_id=int(target_msg_id), text=text, parse_mode="Markdown"
                    )
                    return
                except Exception:
                    pass  # Fallback to send_message if edit fails

            await _telegram_app.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
        # Note: In a production system, we might re-queue this message to a dead-letter queue


# ==========================================
# Inbound Handlers (Producer)
# ==========================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="🚀 Nexus Agent Online. I am connected via Universal MQ."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Send me a message, and I will queue it for the Agent."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Security Check
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS and "*" not in ALLOWED_USER_IDS:
        logger.warning(f"Unauthorized access attempt from Telegram User: {user_id}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⛔ Unauthorized access.")
        return

    user_text = update.message.text
    chat_id = str(update.effective_chat.id)

    # 1. Send Instant Status Message
    status_msg = await context.bot.send_message(
        chat_id=chat_id, text="🚀 **Nexus is thinking...**", parse_mode="Markdown"
    )

    # 2. Create UnifiedMessage with target_message_id
    msg = UnifiedMessage(
        channel=ChannelType.TELEGRAM,
        channel_id=chat_id,
        content=user_text,
        msg_type=MessageType.TEXT,
        meta={
            "telegram_user_id": user_id,
            "telegram_username": update.effective_user.username,
            "telegram_message_id": update.message.message_id,
            "target_message_id": str(status_msg.message_id),  # Critical: Link to status msg
        },
    )

    # 3. Push to Inbox
    await MQService.push_inbox(msg)


async def run_telegram_bot():
    """Starts the Telegram Bot polling loop."""
    if not TELEGRAM_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram Interface disabled.")
        return

    global _telegram_app

    # Build Custom Request object
    from telegram.request import HTTPXRequest

    request = HTTPXRequest(connection_pool_size=8, read_timeout=30.0, write_timeout=30.0, connect_timeout=30.0)

    builder = ApplicationBuilder().token(TELEGRAM_TOKEN).request(request)

    # Check for Proxy
    proxy_url = os.getenv("TELEGRAM_PROXY_URL")
    if proxy_url:
        logger.info(f"Using Telegram Proxy: {proxy_url}")
        builder = builder.proxy_url(proxy_url).get_updates_proxy_url(proxy_url)

    application = builder.build()
    _telegram_app = application

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Register Outbound Handler with Dispatcher
    InterfaceDispatcher.register_handler(ChannelType.TELEGRAM, send_telegram_message)

    logger.info("Starting Telegram Bot Polling...")
    await application.initialize()
    await application.start()

    # Optimized Polling
    await application.updater.start_polling(poll_interval=2.0, bootstrap_retries=-1, drop_pending_updates=False)


async def broadcast_message(text: str):
    """
    Broadcasts a message to all allowed Telegram users via the MQ Outbox.
    """
    if not ALLOWED_USER_IDS or ALLOWED_USER_IDS == [""]:
        logger.warning("No allowed users configured for broadcast.")
        return

    for user_id in ALLOWED_USER_IDS:
        if not user_id or user_id.strip() == "*":
            continue

        msg = UnifiedMessage(
            channel=ChannelType.TELEGRAM,
            channel_id=user_id.strip(),
            content=text,
            msg_type=MessageType.TEXT,
            meta={"is_broadcast": True},
        )
        await MQService.push_outbox(msg)
