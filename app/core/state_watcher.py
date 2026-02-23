import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

import websockets
from sqlmodel import select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.mq import ChannelType, MQService, UnifiedMessage
from app.models.watch_rule import WatchRule

logger = logging.getLogger(__name__)


class StateWatcher:
    _instance = None
    _running = False
    _task = None

    def __init__(self):
        self.url = settings.HOMEASSISTANT_URL
        self.token = settings.HOMEASSISTANT_TOKEN
        if self.url:
            self.ws_url = self.url.replace("http", "ws").rstrip("/") + "/api/websocket"
        else:
            self.ws_url = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = StateWatcher()
        return cls._instance

    async def start(self):
        if not self.ws_url or not self.token:
            logger.warning("Home Assistant URL or Token not set. StateWatcher disabled.")
            return

        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("StateWatcher background task started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("StateWatcher stopped.")

    async def _loop(self):
        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # 1. Auth Phase
                    auth_req = await ws.recv()
                    auth_data = json.loads(auth_req)
                    if auth_data.get("type") != "auth_required":
                        logger.error(f"Unexpected auth message: {auth_data}")
                        await asyncio.sleep(10)
                        continue

                    await ws.send(json.dumps({"type": "auth", "access_token": self.token}))

                    auth_res = await ws.recv()
                    auth_res_data = json.loads(auth_res)
                    if auth_res_data.get("type") != "auth_ok":
                        logger.error(f"HA Auth failed: {auth_res_data}")
                        await asyncio.sleep(60)
                        continue

                    logger.info("StateWatcher connected to HA WebSocket successfully.")

                    # 2. Subscribe to events
                    await ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": "state_changed"}))

                    # 3. Event Loop
                    async for message in ws:
                        if not self._running:
                            break

                        data = json.loads(message)
                        if data.get("type") == "event":
                            event = data.get("event", {})
                            if event.get("event_type") == "state_changed":
                                await self._handle_state_change(event.get("data", {}))

            except Exception as e:
                logger.error(f"StateWatcher connection error: {e}")
                if self._running:
                    await asyncio.sleep(10)

    async def _handle_state_change(self, data: Dict[str, Any]):
        entity_id = data.get("entity_id")
        new_state = data.get("new_state")
        if not new_state:
            return

        state_value = new_state.get("state")

        # Load active rules from DB
        async with AsyncSessionLocal() as session:
            statement = select(WatchRule).where(WatchRule.entity_pattern == entity_id, WatchRule.is_active)
            results = await session.execute(statement)
            rules = results.scalars().all()

            for rule in rules:
                await self._process_rule(rule, entity_id, state_value, session)

    async def _process_rule(self, rule: WatchRule, entity_id: str, state_value: Any, session):
        # 1. Check Cooldown
        if rule.last_triggered_at:
            elapsed = (datetime.utcnow() - rule.last_triggered_at).total_seconds()
            if elapsed < (rule.cooldown_minutes * 60):
                return

        # 2. Evaluate Condition
        # Safety note: Using eval() on user-defined strings.
        # In a real OS, we should use a safer parser.
        triggered = False
        try:
            # Prepare context for evaluation
            # If state is numeric, convert it
            val = state_value
            try:
                if "." in str(val):
                    val = float(val)
                else:
                    val = int(val)
            except ValueError:
                pass

            # Build expression: "val < 2"
            expression = f"val {rule.condition}"
            # Restricted globals/locals
            triggered = eval(expression, {"__builtins__": {}}, {"val": val})
        except Exception as e:
            logger.warning(f"Failed to evaluate rule {rule.id} condition '{rule.condition}': {e}")
            return

        if triggered:
            logger.info(f"🚨 WatchRule {rule.id} triggered for {entity_id} (state={state_value})")

            # Update last triggered
            rule.last_triggered_at = datetime.utcnow()
            session.add(rule)
            await session.commit()

            # 3. Execute Action
            if rule.action == "notify":
                custom_msg = rule.payload.get("message")
                msg_text = (
                    custom_msg
                    if custom_msg
                    else f"Watch Alert: `{entity_id}` is now `{state_value}` (Condition: {rule.condition})"
                )

                # Push to MQ Outbox
                notification = UnifiedMessage(
                    content=msg_text,
                    channel=ChannelType.TELEGRAM,  # Default to TG for alerts
                    user_id=str(rule.user_id),
                    meta={"source": "state_watcher", "entity_id": entity_id},
                )
                await MQService.push_outbox(notification)

            elif rule.action == "agent_prompt":
                # FUTURE: Push to Agent Inbox to let it "think"
                pass
