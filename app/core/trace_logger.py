import logging
import os
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
        session_id: str = None,
        user_id: int = None,
    ):
        if not TraceLogger.is_enabled():
            return

        try:
            from app.core.db import AsyncSessionLocal
            from app.models.llm_trace import LLMTrace

            trace = LLMTrace(
                trace_id=trace_id,
                session_id=session_id,
                user_id=user_id,
                model=model,
                phase=phase,
                prompt_summary=prompt_summary[:2000],
                response_summary=response_summary[:2000],
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


trace_logger = TraceLogger()
