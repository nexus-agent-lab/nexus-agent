from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Literal, TypedDict

from app.core.tool_metadata import ToolCapabilityMetadata, get_tool_metadata

logger = logging.getLogger("nexus.tool_executor")


class ToolExecutionOutcome(TypedDict, total=False):
    """Normalized tool execution result consumed by the graph layer."""

    tool_name: str
    worker: str
    status: Literal["success", "error"]
    raw_text: str
    structured_data: dict | list | None
    exception_text: str | None
    latency_ms: float
    fingerprint: str
    metadata: ToolCapabilityMetadata


def _normalize_args(args: dict[str, Any] | None) -> dict[str, Any]:
    if not args:
        return {}
    return {key: value for key, value in sorted(args.items()) if value is not None}


def build_tool_fingerprint(tool_name: str, args: dict[str, Any] | None = None, selected_skill: str | None = None) -> str:
    """Create a stable fingerprint for duplicate-failure detection."""

    payload = {
        "tool_name": tool_name,
        "selected_skill": selected_skill,
        "args": _normalize_args(args),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _extract_structured_data(raw_text: str) -> dict | list | None:
    if not raw_text:
        return None

    text = raw_text.strip()
    if not text.startswith(("{", "[")):
        return None

    try:
        parsed = json.loads(text)
    except Exception:
        return None

    if isinstance(parsed, (dict, list)):
        return parsed
    return None


class ToolExecutor:
    """Thin runtime adapter that normalizes tool execution outcomes."""

    @staticmethod
    async def execute(
        tool: Any,
        args: dict[str, Any] | None = None,
        *,
        worker: str = "chat_worker",
        selected_skill: str | None = None,
    ) -> ToolExecutionOutcome:
        tool_name = getattr(tool, "name", "unknown_tool")
        metadata = get_tool_metadata(tool)
        fingerprint = build_tool_fingerprint(tool_name, args=args, selected_skill=selected_skill)
        normalized_args = _normalize_args(args)

        started_at = time.perf_counter()
        try:
            result = await tool.ainvoke(normalized_args)
            raw_text = str(result)
            latency_ms = (time.perf_counter() - started_at) * 1000

            return ToolExecutionOutcome(
                tool_name=tool_name,
                worker=worker,
                status="success",
                raw_text=raw_text,
                structured_data=_extract_structured_data(raw_text),
                exception_text=None,
                latency_ms=latency_ms,
                fingerprint=fingerprint,
                metadata=metadata,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - started_at) * 1000
            logger.warning("Tool execution failed for %s: %s", tool_name, exc)
            return ToolExecutionOutcome(
                tool_name=tool_name,
                worker=worker,
                status="error",
                raw_text="",
                structured_data=None,
                exception_text=str(exc),
                latency_ms=latency_ms,
                fingerprint=fingerprint,
                metadata=metadata,
            )
