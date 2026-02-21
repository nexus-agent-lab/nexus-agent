import asyncio
import logging
import sys
import os
import time

# Ensure the app module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.mq import MQService, UnifiedMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("retry_dlq")


async def main():
    logger.info("Starting DLQ Retry Script...")
    r = await MQService.get_redis()

    dlq_len = await r.llen(MQService.DLQ_KEY)
    if dlq_len == 0:
        logger.info("DLQ is empty. Nothing to retry.")
        return

    logger.info(f"Found {dlq_len} messages in DLQ. Moving them to OUTBOX...")

    count = 0
    while True:
        data = await r.rpop(MQService.DLQ_KEY)
        if not data:
            break

        try:
            msg = UnifiedMessage.model_validate_json(data)
            # Remove DLQ meta to give it a fresh start
            msg.meta.pop("dlq_error", None)
            msg.meta.pop("dlq_timestamp", None)

            # Push back to normal outbox
            await r.lpush(MQService.OUTBOX_KEY, msg.model_dump_json())
            count += 1
            logger.info(f"Requeued message {msg.id} for {msg.channel.value}")
        except Exception as e:
            logger.error(f"Failed to process DLQ message: {e}")

    logger.info(f"Successfully requeued {count} messages.")


if __name__ == "__main__":
    asyncio.run(main())
