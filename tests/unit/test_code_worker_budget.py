from langchain_core.messages import AIMessage, ToolMessage

from app.core.agent import should_reflect


def test_code_worker_budget_exhaustion_stops_reflexion():
    state = {
        "messages": [
            AIMessage(content="", tool_calls=[]),
            ToolMessage(content="Execution Error", name="python_sandbox", tool_call_id="call-budget"),
        ],
        "retry_count": 0,
        "selected_worker": "code_worker",
        "attempts_by_worker": {"code_worker": 3},
        "last_classification": {
            "category": "retryable_runtime_error",
            "retryable": False,
            "requires_handoff": True,
            "suggested_next_action": "handoff",
        },
    }

    assert should_reflect(state) == "agent"


def test_code_worker_report_hint_routes_to_report():
    state = {
        "messages": [
            AIMessage(content="", tool_calls=[]),
            ToolMessage(content="Execution blocked", name="python_sandbox", tool_call_id="call-report"),
        ],
        "retry_count": 0,
        "selected_worker": "code_worker",
        "next_execution_hint": "report",
        "last_classification": {
            "category": "non_retryable_runtime_error",
            "retryable": False,
            "requires_handoff": True,
            "suggested_next_action": "handoff",
        },
    }

    assert should_reflect(state) == "report"


def test_code_worker_verify_hint_skips_reflexion():
    state = {
        "messages": [
            AIMessage(content="", tool_calls=[]),
            ToolMessage(content="ok", name="python_sandbox", tool_call_id="call-verify"),
        ],
        "retry_count": 0,
        "selected_worker": "code_worker",
        "next_execution_hint": "verify",
        "last_classification": {
            "category": "success",
            "retryable": False,
            "requires_handoff": False,
            "suggested_next_action": "verify",
        },
    }

    assert should_reflect(state) == "agent"
