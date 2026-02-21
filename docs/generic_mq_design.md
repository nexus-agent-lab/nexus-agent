# Universal Message Queue Architecture

To ensure high reliability and extensibility for multiple platforms (Telegram, Feishu, DingTalk), we will implement a persistent **Universal Message Queue** using Redis.

## 1. Core Concept
Decouple the **Interface Layer** (Telegram/Feishu) from the **Agent Core**.
- **Interfaces** are dumb pipes: they just push to `Inbox` and pop from `Outbox`.
- **Agent Core** is the worker: it consumes `Inbox`, thinks, and pushes to `Outbox`.

## 2. Data Schema (`UnifiedMessage`)
All messages are normalized to this JSON format before entering the queue.

```json
{
  "id": "uuid-v4",
  "channel": "telegram | feishu | dingtalk",
  "channel_id": "12345678 (chat_id)",
  "user_id": "nexus_user_id (optional)",
  "content": "Hello World",
  "type": "text | voice | image",
  "meta": {
    "telegram_message_id": 999,
    "feishu_msg_id": "om_xxx"
  },
  "created_at": 1715000000
}
```

## 3. Queue Structure (Redis)

### `mq:inbox` (List)
- **Producers**: Telegram Poller, Feishu Webhook.
- **Consumer**: Agent Core Worker.
- **Flow**: User sends message -> Interface wraps it -> `LPUSH mq:inbox`.

### `mq:outbox` (List)
- **Producer**: Agent Core (after thinking).
- **Consumer**: Interface Dispatcher.
- **Flow**: Agent finishes -> `LPUSH mq:outbox`.

## 4. Components

### A. `MQService` (`app/core/mq.py`)
- `push_inbox(msg)`
- `pop_inbox()`
- `push_outbox(msg)`
- `pop_outbox()`

### B. `InterfaceDispatcher` (`app/core/dispatcher.py`)
- Background task running `while True`.
- Pops from `mq:outbox`.
- Checks `msg.channel`.
- Routes to specific adapter:
    - `telegram.send_message(...)`
    - `feishu.send_message(...)`

## 5. Reliability Benefits
- **Persistence**: Redis AOF ensures messages aren't lost on restart.
- **Throttling**: Dispatcher can rate-limit sending (e.g., 30 msgs/sec for Telegram) independently of Agent speed.
- **Decoupling**: Adding Feishu just means adding a new Adapter; the Agent core doesn't change.
