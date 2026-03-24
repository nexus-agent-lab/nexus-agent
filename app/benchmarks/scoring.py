from __future__ import annotations

from app.benchmarks.models import AttemptResult, BenchmarkSummary


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def normalize_speed(avg_tps: float, fastest_tps: float) -> float:
    if fastest_tps <= 0:
        return 0.0
    return max(0.0, min(1.0, avg_tps / fastest_tps))


def build_summary(
    *,
    benchmark_id: str,
    suite_id: str,
    suite_version: int,
    model: str,
    attempts: list[AttemptResult],
    environment: dict,
    normalized_speed: float,
) -> BenchmarkSummary:
    total_attempts = len(attempts)
    total_tool_calls = sum(len(attempt.tool_calls) for attempt in attempts)
    successes = sum(1 for attempt in attempts if attempt.metrics.success)
    grounded = sum(1 for attempt in attempts if attempt.metrics.grounded_response)
    complete = sum(1 for attempt in attempts if attempt.metrics.complete_response)
    hallucinations = sum(1 for attempt in attempts if attempt.metrics.hallucination)
    correct_tool = sum(1 for attempt in attempts if attempt.metrics.correct_tool_selection)
    total_wrong_tools = sum(attempt.metrics.wrong_tool_count for attempt in attempts)
    total_unnecessary_tools = sum(attempt.metrics.unnecessary_tool_call_count for attempt in attempts)
    total_format_errors = sum(attempt.metrics.format_error_count for attempt in attempts)
    total_retries = sum(attempt.metrics.retry_count for attempt in attempts)
    total_latency = sum(attempt.metrics.total_completion_time for attempt in attempts)
    total_tps = sum(attempt.metrics.tokens_per_second for attempt in attempts)
    order_matches = sum(
        1
        for attempt in attempts
        if [tool.name for tool in attempt.tool_calls] == attempt.metadata.get("ideal_tool_order", [])
    )

    success_rate = _safe_div(successes, total_attempts)
    format_error_rate = _safe_div(total_format_errors, total_tool_calls)
    hallucination_rate = _safe_div(hallucinations, total_attempts)
    correct_tool_rate = _safe_div(correct_tool, total_attempts)
    wrong_tool_rate = _safe_div(total_wrong_tools, total_tool_calls)
    unnecessary_tool_rate = _safe_div(total_unnecessary_tools, total_tool_calls)
    grounded_rate = _safe_div(grounded, total_attempts)
    complete_rate = _safe_div(complete, total_attempts)
    avg_retry = _safe_div(total_retries, total_attempts)
    retry_rate = min(1.0, avg_retry / 3.0)
    response_deviation_rate = 1.0 - grounded_rate
    tool_order_correctness_rate = _safe_div(order_matches, total_attempts)
    avg_latency = _safe_div(total_latency, total_attempts)
    avg_tps = _safe_div(total_tps, total_attempts)

    final_score = (
        (0.30 * correct_tool_rate)
        + (0.25 * grounded_rate)
        + (0.20 * (1.0 - format_error_rate))
        + (0.15 * (1.0 - retry_rate))
        + (0.10 * normalized_speed)
    )

    return BenchmarkSummary(
        suite_id=suite_id,
        suite_version=suite_version,
        benchmark_id=benchmark_id,
        model=model,
        environment=environment,
        speed={
            "tokens_per_second": round(avg_tps, 4),
            "avg_latency": round(avg_latency, 4),
            "total_completion_time": round(avg_latency, 4),
        },
        tool_effectiveness={
            "correct_tool_selection_rate": round(correct_tool_rate, 4),
            "wrong_tool_selection_rate": round(wrong_tool_rate, 4),
            "unnecessary_tool_call_rate": round(unnecessary_tool_rate, 4),
            "tool_order_correctness_rate": round(tool_order_correctness_rate, 4),
        },
        response_quality={
            "grounded_response_rate": round(grounded_rate, 4),
            "complete_response_rate": round(complete_rate, 4),
            "response_deviation_rate": round(response_deviation_rate, 4),
        },
        accuracy={
            "success_rate": round(success_rate, 4),
            "format_error_rate": round(format_error_rate, 4),
            "hallucination_rate": round(hallucination_rate, 4),
        },
        stability={"avg_retry": round(avg_retry, 4)},
        final_score=round(final_score, 4),
    )
