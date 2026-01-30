import logging
import os

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from app.core.auth_service import AuthService
from app.core.dispatcher import InterfaceDispatcher
from app.core.i18n import get_text
from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage
from app.core.session import SessionManager

logger = logging.getLogger("nexus.telegram")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_IDS = os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",")

# Global reference to Telegram Application (for outbound sending)
_telegram_app = None

# ==========================================
# Localization / I18n
# ==========================================

STRINGS = {
    "en": {
        "welcome": "🚀 **Nexus Agent Online**\n\nI'm connected and ready to assist.\n\n**Available Commands:**\n• `/help` - Show this message\n• `/bind <code>` - Link your account\n• `/unbind` - Unlink your account\n• `/reset` - Clear conversation history\n\nJust send me a message to get started!",
        "bind_prompt": "⚠️ Please provide a 6-digit bind code.\nExample: `/bind 123456`",
        "bind_invalid": "❌ Invalid or expired bind code. Please generate a new one from the Dashboard.",
        "bind_success": "✅ **Success!** Your Telegram account is now linked to Nexus User #{user_id}.\nYou can now send me messages!",
        "bind_fail": "❌ Failed to link account. Please contact support.",
        "bind_conflict_provider": "⚠️ This Telegram account is already linked to another Nexus User.\nPlease unbind it from that user first.",
        "bind_conflict_user": "⚠️ Your Nexus User is already linked to another Telegram account.\nPlease unbind the old account in the Dashboard first.",
        "unbind_success": "✅ **Unbound!** Your Telegram account has been unlinked from Nexus.\nYou are now in Guest mode.",
        "unbind_fail": "⚠️ Your account was not linked.",
        "reset_need_bind": "⚠️ You need to `/bind` your account first.",
        "reset_success": "✅ Conversation history cleared! Starting fresh.",
        "unauthorized": "⛔ Unauthorized access.",
        "typing": "typing...",
        "cmd_help": "Show help and available commands",
        "cmd_bind": "Link your account using a code",
        "cmd_unbind": "Unlink your Telegram account",
        "cmd_unbind": "Unlink your Telegram account",
        "cmd_reset": "Clear your conversation history",
        "welcome_guest": "👋 **Welcome to Nexus!**\n\nI don't recognize this account yet. To use the agent, please link your account:\n\n1. Contact your Administrator to generate a **Bind Token** from the Dashboard.\n2. Send `/bind <token>` here.",
    },
    "zh": {
        "welcome": "🚀 **Nexus Agent 已上线**\n\n我已经连接并准备好为您服务。\n\n**可用指令：**\n• `/help` - 显示此帮助信息\n• `/bind <code>` - 绑定您的账户\n• `/unbind` - 解除账户绑定\n• `/reset` - 清除对话历史\n\n直接发送消息即可开始！",
        "bind_prompt": "⚠️ 请提供6位绑定代码。\n示例：`/bind 123456`",
        "bind_invalid": "❌ 绑定代码无效或已过期。请从仪表板生成一个新的代码。",
        "bind_success": "✅ **成功！** 您的 Telegram 账户已关联至 Nexus 用户 #{user_id}。\n您现在可以向我发送消息了！",
        "bind_fail": "❌ 绑定失败。请联系支持。",
        "bind_conflict_provider": "⚠️ 此 Telegram 账户已关联至另一个 Nexus 用户。\n请先从由于该用户解绑。",
        "bind_conflict_user": "⚠️ 您的 Nexus 用户已关联了另一个 Telegram 账户。\n请先在仪表板中解绑旧账户。",
        "unbind_success": "✅ **已解绑！** 您的 Telegram 账户已与 Nexus 解除关联。\n您现在处于访客模式。",
        "unbind_fail": "⚠️ 您的账户尚未绑定。",
        "reset_need_bind": "⚠️ 您需要先 `/bind` 绑定您的账户。",
        "reset_success": "✅ 对话历史已清除！重新开始。",
        "unauthorized": "⛔ 未授权访问。",
        "typing": "正在输入...",
        "cmd_help": "显示帮助和可用指令",
        "cmd_bind": "使用代码绑定账户",
        "cmd_unbind": "解除 Telegram 账户绑定",
        "cmd_reset": "清除对话历史",
        "welcome_guest": "👋 **欢迎来到 Nexus!**\n\n我暂时还不认识这个账户。请先绑定您的账户：\n\n1. 联系您的管理员从仪表板生成 **绑定代码**。\n2. 发送 `/bind <代码>` 给我们。",
    },
}





async def get_user_language(user_id: str, effective_lang: str = "en") -> str:
    """Determine user language preference from DB or Telegram."""
    try:
        user = await AuthService.get_user_by_identity("telegram", user_id)
        if user and hasattr(user, "language") and user.language:
            return user.language
    except Exception:
        pass
    return effective_lang or "en"


def split_message(text: str, limit: int = 4000) -> list[str]:
    """Splits a message into chunks within the character limit."""
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


async def robust_send_message(bot, chat_id: str, text: str, parse_mode: str = "Markdown", **kwargs):
    """
    Sends a message with automatic chunking and fallback to plain text if parsing fails.
    """
    chunks = split_message(text)
    for chunk in chunks:
        try:
            await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=parse_mode, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if "can't parse entities" in error_str or "parse_mode" in error_str:
                logger.warning(f"Telegram parsing failed for {chat_id}, falling back to plain text. Error: {e}")
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode=None, **kwargs)
            else:
                raise e


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
            # Handle chat actions like 'typing'
            # We don't have user context here easily to determine language, default to EN or use provided content
            # If content is empty, use default "typing"
            action = msg.content if msg.content else "typing"
            await _telegram_app.bot.send_chat_action(chat_id=chat_id, action=action)
        else:
            # Send new message (or final replacement)
            if target_msg_id:
                # If we have a target, try to edit it first
                try:
                    await _telegram_app.bot.edit_message_text(
                        chat_id=chat_id, message_id=int(target_msg_id), text=text, parse_mode="Markdown"
                    )
                    return
                except Exception:
                    pass  # Fallback to new message if edit fails (e.g. message too old)

            # Use Robust Send
            await robust_send_message(_telegram_app.bot, chat_id=chat_id, text=text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
        # Note: In a production system, we might re-queue this message to a dead-letter queue

    # Handle Unpinning (e.g., after final answer)
    unpin_id = msg.meta.get("unpin_message_id")
    if unpin_id:
        try:
            await _telegram_app.bot.unpin_chat_message(chat_id=chat_id, message_id=int(unpin_id))
        except Exception as e:
            logger.warning(f"Failed to unpin message {unpin_id}: {e}")

    # Handle Helper Commands Update (Dynamic Menu)
    commands_meta = msg.meta.get("telegram_commands")
    if commands_meta:
        try:
            from telegram import BotCommand, BotCommandScopeChat
            cmds = [BotCommand(command=c["command"], description=c["description"]) for c in commands_meta]
            # Update commands for this specific chat
            await _telegram_app.bot.set_my_commands(commands=cmds, scope=BotCommandScopeChat(chat_id=chat_id))
            logger.info(f"Updated Telegram commands for {chat_id}: {len(cmds)} commands")
        except Exception as e:
            logger.warning(f"Failed to set Telegram commands for {chat_id}: {e}")


# ==========================================
# Inbound Handlers (Producer)
# ==========================================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    lang = await get_user_language(user_id, update.effective_user.language_code)

    help_text = get_text("welcome", lang)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=help_text, parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reuse start command for consistency
    await start(update, context)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset conversation history for the current user."""
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    lang = await get_user_language(user_id, update.effective_user.language_code)

    try:

        # Resolve user
        user = await AuthService.get_user_by_identity("telegram", user_id)

        if not user:
            await context.bot.send_message(
                chat_id=chat_id, text=get_text("reset_need_bind", lang)
            )
            return

        # Clear session history
        session = await SessionManager.get_or_create_session(user.id)
        await SessionManager.clear_history(session.id)

        await context.bot.send_message(
            chat_id=chat_id, text=get_text("reset_success", lang), parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Failed to reset session: {e}", exc_info=True)
        # Fallback error message (usually code error, keep EN)
        await context.bot.send_message(
            chat_id=chat_id, text="❌ Failed to reset session. Please try again later."
        )


async def bind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Link a Telegram identity to an existing Nexus user account."""
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    # Don't check DB for lang here to be fast, use telegram pref
    lang = update.effective_user.language_code

    if not context.args:
        # Interactive mode: Ask user for token
        await context.bot.send_message(
            chat_id=chat_id,
            text=get_text("bind_prompt", lang), # "Please enter code..."
            parse_mode="Markdown"
        )
        # Set state in user_data
        context.user_data["awaiting_bind_token"] = True
        return

    token = context.args[0]
    await process_bind_token(update, context, token, lang)

    
async def process_bind_token(update: Update, context: ContextTypes.DEFAULT_TYPE, token: str, lang: str):
    """Core logic to process the bind token."""
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)

    logger.info(f"Processing bind token {token} for User {user_id}")
    try:
        # 1. Verify Token
        target_user_id = await AuthService.verify_bind_token(token)
        if not target_user_id:
            logger.warning(f"Invalid or expired bind token {token} for Telegram user {user_id}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=get_text("bind_invalid", lang)
            )
            return

        # 2. Perform Binding
        username = update.effective_user.username or update.effective_user.first_name
        logger.info(f"Token verified. Binding Telegram ID {user_id} to Nexus User #{target_user_id}")

        success = await AuthService.bind_identity(
            user_id=target_user_id,
            provider="telegram",
            provider_user_id=user_id,
            username=username
        )

        if success:
            logger.info(f"Account bind successful for {user_id}")

            # Update user language if possible based on Telegram pref
            if lang:
                from app.core.db import AsyncSessionLocal
                from app.models.user import User
                async with AsyncSessionLocal() as session:
                    u = await session.get(User, target_user_id)
                    if u:
                        u.language = "zh" if lang.startswith("zh") else "en"
                        session.add(u)
                        await session.commit()

            await context.bot.send_message(
                chat_id=chat_id,
                text=get_text("bind_success", lang, user_id=target_user_id),
                parse_mode="Markdown"
            )
        else:
            logger.warning(f"Account bind failed for {user_id}. Conflict or already linked.")
            from app.core.auth_service import BindResult
            # Check result if possible, assuming success is returned as bool or enum
            # If changed to Enum, need to handle it. 
            # Previous changes returned BindResult. 
            # Let's check the code I recall: 'success = await AuthService.bind_identity...' 
            # Wait, I previously changed it to return BindResult Enum! 
            # I should handle Enum here.
            
            if success == BindResult.PROVIDER_CONFLICT:
                 text = get_text("bind_conflict_provider", lang)
            elif success == BindResult.USER_CONFLICT:
                 text = get_text("bind_conflict_user", lang)
            else:
                 text = get_text("bind_fail", lang)
                 
            await context.bot.send_message(chat_id=chat_id, text=text)

    except Exception as e:
        logger.error(f"Failed to bind account: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ An error occurred during binding. Please try again later."
        )



async def unbind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlink the current Telegram identity from Nexus account."""
    user_id = str(update.effective_user.id)
    chat_id = str(update.effective_chat.id)
    lang = await get_user_language(user_id, update.effective_user.language_code)

    try:
        success = await AuthService.unbind_identity("telegram", user_id)

        if success:
            await context.bot.send_message(
                chat_id=chat_id,
                text=get_text("unbind_success", lang),
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=get_text("unbind_fail", lang)
            )
    except Exception as e:
        logger.error(f"Failed to unbind: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ An error occurred during unbinding."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # 0. Check for interactive bind state
    if context.user_data.get("awaiting_bind_token"):
        # Create task to process bind (fire and forget check, or await?)
        # Await is better for user feedback
        token = update.message.text.strip()
        context.user_data.pop("awaiting_bind_token", None)
        lang = update.effective_user.language_code
        await process_bind_token(update, context, token, lang)
        return

    # Security Check
    if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS and "*" not in ALLOWED_USER_IDS:
        logger.warning(f"Unauthorized access attempt from Telegram User: {user_id}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=get_text("unauthorized"))
        return

    user_text = update.message.text
    chat_id = str(update.effective_chat.id)

    # 1. Show Typing Status immediately
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # 2. Create UnifiedMessage
    msg = UnifiedMessage(
        channel=ChannelType.TELEGRAM,
        channel_id=chat_id,
        content=user_text,
        msg_type=MessageType.TEXT,
        meta={
            "telegram_user_id": user_id,
            "telegram_username": update.effective_user.username,
            "telegram_message_id": update.message.message_id,
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
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("bind", bind_command))
    application.add_handler(CommandHandler("unbind", unbind_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Register Outbound Handler with Dispatcher
    InterfaceDispatcher.register_handler(ChannelType.TELEGRAM, send_telegram_message)

    logger.info("Starting Telegram Bot Polling...")
    await application.initialize()

    # Set Global Command Menu (Localized)
    try:
        from telegram import BotCommand

        # English Menu
        cmds_en = [
            BotCommand("help", get_text("cmd_help", "en")),
            BotCommand("bind", get_text("cmd_bind", "en")),
            BotCommand("unbind", get_text("cmd_unbind", "en")),
            BotCommand("reset", get_text("cmd_reset", "en")),
        ]
        await application.bot.set_my_commands(cmds_en, language_code="en")

        # Chinese Menu
        cmds_zh = [
            BotCommand("help", get_text("cmd_help", "zh")),
            BotCommand("bind", get_text("cmd_bind", "zh")),
            BotCommand("unbind", get_text("cmd_unbind", "zh")),
            BotCommand("reset", get_text("cmd_reset", "zh")),
        ]
        await application.bot.set_my_commands(cmds_zh, language_code="zh")

        # Default fallback (English)
        await application.bot.set_my_commands(cmds_en)

        logger.info("Global localized Telegram command menus updated (EN/ZH).")
    except Exception as e:
        logger.warning(f"Failed to set global Telegram commands: {e}")

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
