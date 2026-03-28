# Session Context Continuation Plan

## Problem

Current multi-turn behavior is inconsistent across channels.

- Message-channel flows already restore recent session history before calling the agent.
- Web `/api/chat` and `/api/chat/stream` accept `thread_id` in the request model but do not use it.
- The backend does not return a reusable session identifier to the caller.
- As a result, follow-up messages like "继续呀", "刚才那个再搜一下", or "按上一步继续" often reach the LLM without prior context.

This creates a poor user experience because the user feels they are in one conversation, while the backend treats many turns as isolated requests.

## Root Cause

### 1. Web chat path skips session restoration

In [`app/main.py`](../../app/main.py), the `/api/chat` and `/api/chat/stream` handlers build:

- `messages=[HumanMessage(content=request.message)]`
- `user=current_user`
- `trace_id=...`

But they do not:

- resolve a `Session` from `request.thread_id`
- load `SessionSummary` + recent `SessionMessage`
- inject those messages into the initial graph state
- set `session_id` so the graph can persist the new turn

### 2. Session persistence already exists, but only works when `session_id` is present

The session subsystem is already usable:

- [`app/core/session.py`](../../app/core/session.py) supports `get_or_create_session(...)`
- it can return `get_history_with_summary(...)`
- [`app/core/agent.py`](../../app/core/agent.py) already persists messages when `state["session_id"]` exists
- [`app/core/worker.py`](../../app/core/worker.py) already implements the right pattern for message-channel flows

So the main gap is not storage capability. The gap is that the web path never joins this protocol.

### 3. No end-to-end conversation contract

There is currently no unified rule for:

- how a client starts a new conversation
- how it resumes an existing conversation
- how the server communicates the canonical conversation identifier back
- how history is loaded, compacted, and truncated consistently across channels

## Design Goals

1. Follow-up turns must inherit enough prior context for normal conversational continuity.
2. All chat entry points should share one session contract.
3. The LLM input should remain bounded in token size.
4. The server should stay authoritative for history selection and compaction.
5. The client should not need to replay full history on every request.
6. The design should work for web, Telegram, WeChat, voice, and future channels.

## Proposed Architecture

### A. Introduce a canonical conversation identity

Adopt one user-visible contract:

- `thread_id` means the canonical conversation identifier exposed to clients
- it maps directly to `Session.session_uuid`

Rules:

- If the client sends no `thread_id`, the server creates a new session.
- If the client sends a valid `thread_id` owned by the current user, the server resumes that session.
- If the client sends an unknown `thread_id`, the server creates a new session and returns the new id.
- The server always returns the canonical `thread_id` in the response.

This makes continuation explicit and debuggable.

### B. Unify session bootstrapping behind one helper

Extract the session restore logic into a shared helper, for example:

`app/core/chat_session_bootstrap.py`

Suggested contract:

```python
async def build_session_state(
    *,
    user: User,
    incoming_message: str,
    thread_id: str | None,
    history_limit: int = 10,
) -> tuple[dict, Session]:
    ...
```

Responsibilities:

- resolve or create the session
- load compacted summary plus recent raw history
- convert stored rows into LangChain messages
- prepend summary as a system message when present
- append the incoming human message
- return:
  - the prepared `initial_state`
  - the resolved `Session`

Then both:

- `app/main.py` web handlers
- `app/core/worker.py` channel handlers

reuse the same bootstrap logic instead of duplicating it.

### C. Make response payloads session-aware

Extend `ChatResponse` with:

- `thread_id: str`
- optionally `created_new_thread: bool`

Suggested response shape:

```json
{
  "response": "...",
  "trace_id": "...",
  "thread_id": "...",
  "created_new_thread": false
}
```

For streaming:

- send an early SSE event containing the resolved `thread_id`
- keep the final event payload unchanged except for also including `thread_id`

This lets the frontend persist the conversation id immediately.

### D. Keep server-side history assembly authoritative

The client should send only:

- current turn message
- optional `thread_id`

The server should decide what to inject into the LLM prompt:

- archived summary blocks from `SessionSummary`
- recent raw turns from `SessionMessage`
- current user turn

This is the right tradeoff because:

- it avoids trusting the client for conversation truth
- it reduces request size
- it keeps privacy and token control on the server
- it allows compaction policy changes without frontend changes

### E. Preserve bounded context with a two-tier history policy

Use a stable history loading rule:

- Tier 1: all available compacted summaries merged into one summary block
- Tier 2: last `N` raw messages, default `N=10`

Additional guardrails:

- add a token or character budget for rehydrated raw history
- prefer dropping oldest raw messages before dropping the summary block
- never inject raw tool outputs above the existing pruning limit

This makes "继续" work without unbounded prompt growth.

## Recommended Rollout

### Phase P0: Fix continuity for current chat APIs

Scope:

- wire `/api/chat` to `SessionManager.get_or_create_session(...)`
- load `get_history_with_summary(...)`
- inject prior context before calling the graph
- set `session_id`
- return `thread_id`

Do the same for `/api/chat/stream`.

This alone fixes the main user pain.

### Phase P1: Extract shared bootstrap module

Scope:

- move session restore logic out of `app/core/worker.py`
- create one shared session bootstrap helper
- migrate web, message-channel, and voice paths to that helper

Outcome:

- less drift between channels
- one place to tune context policy

### Phase P2: Add conversation lifecycle APIs

Add endpoints such as:

- `GET /api/chat/threads`
- `GET /api/chat/threads/{thread_id}/messages`
- `POST /api/chat/threads`
- `DELETE /api/chat/threads/{thread_id}` or archive semantics

This supports a real frontend chat list, history viewer, and reset behavior.

### Phase P3: Context quality upgrades

Possible improvements:

- session title generation from early turns
- "semantic recall" of older relevant turns in addition to recency
- better summary refresh triggers
- a small follow-up detector that boosts continuity for messages like "继续", "然后呢", "按刚才那个"

These are useful, but not required to solve the current bug.

## API Contract Proposal

### Request

```json
{
  "message": "继续呀",
  "thread_id": "6b8c0d8f-6d6f-4f6c-96c2-2a2b8b5a1abc"
}
```

### Response

```json
{
  "response": "我继续上一轮的搜索结果……",
  "trace_id": "1d2c3b4a-...",
  "thread_id": "6b8c0d8f-6d6f-4f6c-96c2-2a2b8b5a1abc",
  "created_new_thread": false
}
```

## Backend Flow

1. Receive request with `message` and optional `thread_id`.
2. Resolve the session by `thread_id + current_user.id`.
3. If not found, create a new session.
4. Load:
   - archived summary
   - recent raw messages
5. Construct:
   - `SystemMessage(summary)` if available
   - recent historical messages
   - current `HumanMessage`
6. Set `session_id` in graph state.
7. Invoke the graph.
8. Persist new user/assistant/tool messages through the existing agent hooks.
9. Return `thread_id` with the response.

## Frontend Contract

The frontend should maintain only one durable pointer per active chat tab:

- `activeThreadId`

Behavior:

- first send: no `thread_id`
- server returns `thread_id`
- all subsequent sends include that `thread_id`
- "new chat" clears `activeThreadId`
- chat page reload restores `activeThreadId` from route or local state

Important:

- do not require the frontend to replay prior messages into the request body
- do not let the frontend invent conversation state

## Error and Edge Cases

### Unknown or unauthorized thread_id

If the thread does not belong to the current user:

- do not leak whether it exists
- create a new session or return a generic not-found/forbidden behavior

Recommended default:

- create a new session for UX continuity
- log a warning for debugging

### Missing earlier reply

If the previous turn triggered tools but the final assistant message was never delivered:

- the stored history still exists in the session
- a follow-up like "继续" should continue from the stored assistant/tool state

Longer term, we may want explicit interrupted-run recovery, but the same session contract is the foundation.

### Very long sessions

Rely on the existing compaction path:

- keep summaries
- keep the last few raw turns
- prune oversized tool content

If prompt budgets still become unstable, add a hard token budget when reconstructing raw history.

## Testing Plan

### Unit tests

Add tests for:

- resume by known `thread_id`
- create new session when `thread_id` is missing
- create new session when `thread_id` is invalid
- history summary is injected before recent raw messages
- response returns canonical `thread_id`

### Integration tests

Add a two-turn chat test:

1. send "帮我搜索 X"
2. send "继续呀" with returned `thread_id`
3. assert the second invocation sees prior history

Also add a regression test proving that `/api/chat/stream` returns and reuses the same `thread_id`.

## Recommendation

Implement P0 and P1 together if possible.

Reason:

- P0 alone fixes the immediate bug
- P1 prevents web and message-channel behavior from drifting again

If time is tight, P0 is still worth shipping immediately because it addresses the user-visible failure mode with minimal product risk.

## Concrete Next Step

Recommended implementation order:

1. add a shared session bootstrap helper
2. wire `/api/chat` and `/api/chat/stream` to it
3. extend `ChatResponse` with `thread_id`
4. add regression tests for multi-turn continuation
5. then decide whether to expose thread list/history APIs to the frontend
