import logging
import os
import sys
from typing import Any, Dict, List

logger = logging.getLogger("nexus.trace")


class TraceLogger:
    @staticmethod
    def is_enabled() -> bool:
        return os.getenv("DEBUG_WIRE_LOG", "false").lower() == "true"

    @staticmethod
    async def log_llm_call(
        trace_id: str,
        model: str,
        phase: str,
        prompt_summary: str,
        response_summary: str,
        latency_ms: float,
        tools_bound: List[str] = None,
        tool_calls: List[Dict[str, Any]] = None,
        routing_queries: List[str] = None,
        matched_tools: List[str] = None,
        selected_worker: str = None,
        selected_skill: str = None,
        intent_class: str = None,
        route_confidence: float = None,
        classification: str = None,
        session_id: str = None,
        user_id: int = None,
    ):
        if not TraceLogger.is_enabled():
            return
        # --- stdout wire log (always prints when enabled, independent of DB) ---
        print(
            f"\n{'=' * 60}\n"
            f"🔌 WIRE LOG | {phase} | {model}\n"
            f"{'=' * 60}\n"
            f"⏱  Latency: {latency_ms:.0f}ms\n"
            f"🧭 Intent: {intent_class or '-'}"
            f" | Worker: {selected_worker or '-'}"
            f" | Skill: {selected_skill or '-'}"
            f" | Route: {route_confidence if route_confidence is not None else '-'}\n"
            f"🧪 Classification: {classification or '-'}\n"
            f"🔧 Tools Bound: {', '.join(tools_bound or [])}\n"
            f"📥 Prompt:  {(prompt_summary or '')[:500]}\n"
            f"📤 Response: {(response_summary or '')[:500]}\n"
            f"{'=' * 60}",
            file=sys.stdout,
            flush=True,
        )

        try:
            from app.core.db import AsyncSessionLocal
            from app.models.llm_trace import LLMTrace

            trace = LLMTrace(
                trace_id=str(trace_id),
                session_id=str(session_id) if session_id is not None else "0",
                user_id=user_id,
                model=model,
                phase=phase,
                prompt_summary=prompt_summary[:2000] if prompt_summary else None,
                response_summary=response_summary[:2000] if response_summary else None,
                latency_ms=latency_ms,
                tools_bound=tools_bound,
                tool_calls=tool_calls,
                routing_queries=routing_queries,
                matched_tools=matched_tools,
            )

            async with AsyncSessionLocal() as session:
                session.add(trace)
                await session.commit()

        except Exception as e:
            logger.error(f"Failed to write LLM trace: {e}")

    @staticmethod
    def log_wire_event(
        stage: str,
        *,
        trace_id: str | None = None,
        summary: str | None = None,
        details: Dict[str, Any] | None = None,
    ):
        """
        Human-readable stage log for following graph flow in stdout.

        This is intentionally lightweight and does not write to DB.
        """
        if not TraceLogger.is_enabled():
            return

        lines = [
            f"🔌 FLOW | {stage}",
        ]
        if trace_id:
            lines.append(f"🧵 Trace: {trace_id}")
        if summary:
            lines.append(f"📝 Summary: {summary}")
        if details:
            for key, value in details.items():
                if value in (None, "", [], {}):
                    continue
                rendered = value
                if isinstance(value, list):
                    rendered = ", ".join(str(item) for item in value[:12])
                elif isinstance(value, dict):
                    rendered = ", ".join(f"{k}={v}" for k, v in list(value.items())[:8])
                lines.append(f"• {key}: {rendered}")

        print(
            f"\n{'-' * 60}\n" + "\n".join(lines) + f"\n{'-' * 60}",
            file=sys.stdout,
            flush=True,
        )


trace_logger = TraceLogger()
