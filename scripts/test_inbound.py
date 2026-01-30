import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.mq import ChannelType, MessageType, MQService, UnifiedMessage


async def main():
    chat_id = "999888777"
    user_id = "999888777"

    msg = UnifiedMessage(
        channel=ChannelType.TELEGRAM,
        channel_id=chat_id,
        content="Test message from bound user",
        msg_type=MessageType.TEXT,
        meta={
            "telegram_user_id": user_id,
            "telegram_username": "repro_user",
        },
    )

    print(f"Pushing message from {user_id} to Inbox...")
    await MQService.push_inbox(msg)
    print("Done. Check logs.")


if __name__ == "__main__":
    asyncio.run(main())
