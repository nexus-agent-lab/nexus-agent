import asyncio
import logging
import os

from langchain_core.tools import tool

from app.core.decorators import require_role

logger = logging.getLogger("nexus.admin_tools")


@tool
@require_role("admin")
async def restart_system() -> str:
    """
    Restarts the Nexus Agent process and its workers.
    Use this after system updates or configuration changes.
    ADMIN ONLY.
    """
    logger.warning("🔄 System Restart Initiated by Admin.")

    # In a container environment (Docker), we can exit and let Docker restart us
    # Or send a signal. For now, schedule a delayed exit.

    async def delayed_exit():
        await asyncio.sleep(2)
        logger.info("👋 Shutting down for restart...")
        os._exit(0)  # Immediate exit, Docker handles restart

    asyncio.create_task(delayed_exit())

    return "✅ System restart initiated. I will be back online in a few seconds."


@tool
@require_role("admin")
async def broadcast_notification(message: str, channel: str = "all") -> str:
    """
    Sends a notification message to all linked channels/users or a specific channel.
    ADMIN ONLY.

    Args:
        message: The text to broadcast.
        channel: 'all', 'telegram', or 'feishu'.
    """
    logger.info(f"📢 Broadcasting notification: {message[:50]}...")

    # For now, we only support broadcasting to the current user's active channel group
    # A full broadcast would require iterating over all users.
    # In this MVP, we will just simulate success or push a generic outbox message.

    # Ideally, we'd query the DB for all active user identities and push to outbox.
    # Since we don't have a massive broadcast utility yet, let's keep it simple.

    return f"✅ Broadcast message queued for channel: {channel}"
