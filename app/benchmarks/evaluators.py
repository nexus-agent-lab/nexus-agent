from __future__ import annotations

from app.benchmarks.models import ScenarioDefinition


def response_contains_all(final_response: str, expected_fragments: list[str]) -> bool:
    lowered = final_response.lower()
    return all(fragment.lower() in lowered for fragment in expected_fragments)


def response_contains_forbidden(final_response: str, forbidden_fragments: list[str]) -> bool:
    lowered = final_response.lower()
    return any(fragment.lower() in lowered for fragment in forbidden_fragments)


def evaluate_attempt(
    *,
    scenario: ScenarioDefinition,
    tool_names: list[str],
    final_response: str,
    format_error_count: int,
    retry_count: int,
) -> dict[str, bool | int]:
    expectations = scenario.expectations
    required_tools = expectations.required_tools
    allowed_tools = expectations.allowed_tools or scenario.available_tools

    wrong_tool_count = sum(1 for name in tool_names if name not in allowed_tools)
    unnecessary_tool_call_count = sum(1 for name in tool_names if name not in required_tools)
    correct_tool_selection = all(name in tool_names for name in required_tools) and wrong_tool_count == 0
    grounded_response = response_contains_all(
        final_response, expectations.expected_response_contains
    ) and not response_contains_forbidden(final_response, expectations.forbidden_response_contains)
    complete_response = grounded_response
    hallucination = response_contains_forbidden(final_response, expectations.forbidden_response_contains)
    success = (
        correct_tool_selection
        and grounded_response
        and format_error_count == 0
        and retry_count <= expectations.max_retries
    )

    return {
        "success": success,
        "correct_tool_selection": correct_tool_selection,
        "grounded_response": grounded_response,
        "complete_response": complete_response,
        "hallucination": hallucination,
        "wrong_tool_count": wrong_tool_count,
        "unnecessary_tool_call_count": unnecessary_tool_call_count,
    }
