import logging
from typing import Optional

logger = logging.getLogger("nexus.i18n")

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


def get_text(key: str, lang: str = "en", **kwargs) -> str:
    """Retrieve localized string."""
    lang_code = "zh" if lang and lang.startswith("zh") else "en"
    text = STRINGS.get(lang_code, STRINGS["en"]).get(key, "")
    return text.format(**kwargs) if text else key


def detect_language(text: str) -> str:
    """
    Detect language from text content.
    Returns 'zh' if Chinese characters are present, else 'en'.
    """
    if not text:
        return "en"
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        return "zh"
    return "en"


def resolve_language(user: Optional[object], message_content: str = "") -> str:
    """
    Resolve the best language to use for response.
    Priority:
    1. User's saved language preference (if User object provided and has 'language')
    2. Dynamic detection from current message content
    3. Default to English
    """
    # 1. Check User Preference
    if user and hasattr(user, "language") and user.language:
        # Assuming user.language is reliable (e.g. 'en', 'zh')
        # If it's a valid supported code, return it.
        # Simple check: if it starts with zh, return zh
        if user.language.startswith("zh"):
            return "zh"
        return "en"

    # 2. Dynamic Detection
    return detect_language(message_content)
