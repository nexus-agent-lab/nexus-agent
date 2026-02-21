import asyncio
import logging
from typing import Callable, Dict

from app.core.mq import ChannelType, MQService

logger = logging.getLogger("nexus.dispatcher")


class InterfaceDispatcher:
    """
    Consumes messages from MQ Outbox and routes them to the correct interface adapter.
    """

    _send_handlers: Dict[ChannelType, Callable] = {}
    _running = False
    _task = None

    @classmethod
    async def get_handler(cls, channel: ChannelType):
        if channel == ChannelType.TELEGRAM:
            # Lazy import to avoid circular dependencies
            from app.interfaces.telegram import send_telegram_message

            return send_telegram_message

        elif channel == ChannelType.FEISHU:
            from app.interfaces.feishu import send_feishu_message

            return send_feishu_message

        elif channel == ChannelType.DINGTALK:
            # Placeholder for DingTalk
            # from app.interfaces.dingtalk import send_dingtalk_message
            # return send_dingtalk_message
            pass

        elif channel in cls._send_handlers:  # Corrected from cls._handlers
            return cls._send_handlers[channel]

        return None
        # This line is unreachable due to the return None above it.
        # logger.info(f"Registered Outbound Handler for: {channel.value}")

    @classmethod
    def register_handler(cls, channel: ChannelType, handler: Callable):
        """
        Register a function to handle sending messages for a specific channel.
        Handler signature: async def send(msg: UnifiedMessage)
        """
        cls._send_handlers[channel] = handler
        logger.info(f"Registered Outbound Handler for: {channel.value}")

    @classmethod
    async def start(cls):
        """Start the dispatcher loop."""
        if cls._running:
            return
        cls._running = True
        cls._task = asyncio.create_task(cls._loop())
        logger.info("Interface Dispatcher Started.")

    @classmethod
    async def stop(cls):
        """Stop the dispatcher loop."""
        cls._running = False
        if cls._task:
            cls._task.cancel()
            try:
                await cls._task
            except asyncio.CancelledError:
                pass
        logger.info("Interface Dispatcher Stopped.")

    @classmethod
    async def _loop(cls):
        logger.info("Dispatcher Loop Running...")
        max_retries = 3
        base_delay = 2.0

        while cls._running:
            try:
                msg = await MQService.pop_outbox()

                if msg:
                    handler = cls._send_handlers.get(msg.channel)
                    if handler:
                        success = False
                        last_error = ""

                        for attempt in range(1, max_retries + 1):
                            try:
                                await handler(msg)
                                logger.info(f"Dispatched Outbound: {msg.id} -> {msg.channel.value}")
                                success = True
                                break
                            except Exception as e:
                                last_error = str(e)
                                if attempt < max_retries:
                                    delay = base_delay * (2 ** (attempt - 1))
                                    logger.warning(
                                        f"Failed to send message {msg.id} via {msg.channel.value} (Attempt {attempt}/{max_retries}). "
                                        f"Retrying in {delay}s: {last_error}"
                                    )
                                    await asyncio.sleep(delay)
                                else:
                                    logger.error(
                                        f"Failed to send message {msg.id} via {msg.channel.value} after {max_retries} attempts: {last_error}"
                                    )

                        if not success:
                            await MQService.push_dlq(msg, error_msg=last_error)
                    else:
                        logger.warning(f"No handler registered for channel: {msg.channel.value}")
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dispatcher Error: {e}")
                await asyncio.sleep(1.0)
