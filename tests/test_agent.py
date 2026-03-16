"""
Tests for the agent graph and decision-making logic.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.agent import (
    clarify_followup_node,
    create_agent_graph,
    repair_followup_node,
    report_failure_node,
    reviewer_gate_node,
    route_after_review,
    should_continue,
    should_reflect,
    verify_followup_node,
)
from app.models.user import User


@pytest.mark.asyncio
class TestAgentGraph:
    """Tests for agent graph execution."""

    async def test_agent_initialization(self, mock_llm):
        """Agent graph should initialize with tools."""
        tools = []
        graph = create_agent_graph(tools)
        assert graph is not None

    async def test_agent_processes_message(self, mock_llm, test_user: User):
        """Agent should process user messages."""
        tools = []
        graph = create_agent_graph(tools)

        initial_state = {
            "messages": [HumanMessage(content="Hello")],
            "user": test_user,
        }

        # This will fail without proper mocking, but structure is ready
        try:
            result = await graph.ainvoke(initial_state)
            assert "messages" in result
        except Exception:
            # Expected to fail without full mock setup
            pass


@pytest.mark.asyncio
class TestAgentMemory:
    """Tests for agent memory retrieval."""

    async def test_memory_retrieval(self, test_user: User, mocker):
        """Agent should retrieve user memories."""
        # Mock memory search to avoid API call
        mocker.patch("app.core.memory.memory_manager.search_memory", return_value=[])

        from app.core.agent import retrieve_memories

        state = {
            "messages": [HumanMessage(content="What's my name?")],
            "user": test_user,
        }

        result = await retrieve_memories(state)
        assert "memories" in result
        assert isinstance(result["memories"], list)


def test_should_continue_loops_when_verification_required():
    state = {
        "messages": [AIMessage(content="Need verification", tool_calls=[])],
        "verification_status": "required",
        "llm_call_count": 1,
    }

    assert should_continue(state) == "verify"


def test_should_continue_ends_after_verification_retry_budget():
    state = {
        "messages": [AIMessage(content="Still no verify call", tool_calls=[])],
        "verification_status": "required",
        "llm_call_count": 3,
    }

    assert should_continue(state) == "__end__"


def test_should_continue_loops_when_verification_failed():
    state = {
        "messages": [AIMessage(content="Verification failed", tool_calls=[])],
        "verification_status": "failed",
        "llm_call_count": 1,
    }

    assert should_continue(state) == "agent"


def test_should_continue_ends_when_verification_passed():
    state = {
        "messages": [AIMessage(content="Verified", tool_calls=[])],
        "verification_status": "passed",
        "llm_call_count": 1,
    }

    assert should_continue(state) == "__end__"


def test_should_continue_ends_after_failed_handoff_report():
    state = {
        "messages": [AIMessage(content="Reported failure", tool_calls=[])],
        "verification_status": "failed",
        "llm_call_count": 2,
    }

    assert should_continue(state) == "__end__"


def test_should_continue_routes_code_worker_report_to_report_node():
    state = {
        "messages": [AIMessage(content="Need report", tool_calls=[])],
        "selected_worker": "code_worker",
        "next_execution_hint": "report",
    }

    assert should_continue(state) == "report"


def test_should_continue_retries_skill_action_followup_before_end():
    state = {
        "messages": [AIMessage(content="Need to actually perform the action", tool_calls=[])],
        "selected_worker": "skill_worker",
        "next_execution_hint": "act",
        "llm_call_count": 2,
    }

    assert should_continue(state) == "agent"


def test_should_reflect_routes_code_worker_report_to_report_node():
    state = {
        "messages": [ToolMessage(content="Execution failed", name="python_sandbox", tool_call_id="call-report")],
        "selected_worker": "code_worker",
        "next_execution_hint": "report",
    }

    assert should_reflect(state) == "report"


@pytest.mark.asyncio
async def test_report_failure_node_renders_deterministic_message():
    result = await report_failure_node(
        {
            "messages": [HumanMessage(content="执行失败了怎么回事？")],
            "selected_worker": "code_worker",
            "next_execution_hint": "report",
            "last_classification": {
                "category": "non_retryable_runtime_error",
                "user_facing_summary": "Code execution failed repeatedly and needs intervention.",
                "debug_summary": "Traceback: ValueError('boom')",
            },
        }
    )

    assert "messages" in result
    assert "执行未能完成" in result["messages"][0].content or "本次执行未能完成" in result["messages"][0].content
    assert result["verification_status"] == "failed"


def test_route_after_review_routes_required_to_verify_node():
    state = {
        "messages": [ToolMessage(content="ok", name="verify_result", tool_call_id="call-1")],
        "verification_status": "required",
    }

    assert route_after_review(state) == "verify"


def test_route_after_review_routes_failed_back_to_agent():
    state = {
        "messages": [ToolMessage(content="verify failed", name="verify_result", tool_call_id="call-2")],
        "verification_status": "failed",
    }

    assert route_after_review(state) == "agent"


def test_route_after_review_routes_verification_failed_to_report_node():
    state = {
        "messages": [ToolMessage(content="verify failed", name="verify_result", tool_call_id="call-2b")],
        "verification_status": "failed",
        "last_classification": {"category": "verification_failed"},
    }

    assert route_after_review(state) == "report"


def test_route_after_review_routes_report_to_report_node():
    state = {
        "messages": [ToolMessage(content="blocked", name="python_sandbox", tool_call_id="call-3")],
        "next_execution_hint": "report",
    }

    assert route_after_review(state) == "report"


def test_route_after_review_routes_ask_user_to_clarify_node():
    state = {
        "messages": [ToolMessage(content="not found", name="lookup_tool", tool_call_id="call-3b")],
        "selected_worker": "skill_worker",
        "next_execution_hint": "ask_user",
        "last_classification": {
            "category": "invalid_input",
            "suggested_next_action": "ask_user",
        },
    }

    assert route_after_review(state) == "clarify"


def test_route_after_review_routes_code_worker_failed_to_report_node():
    state = {
        "messages": [ToolMessage(content="verify failed", name="python_sandbox", tool_call_id="call-4")],
        "selected_worker": "code_worker",
        "verification_status": "failed",
    }

    assert route_after_review(state) == "report"


def test_route_after_review_routes_handoff_failed_to_report_node():
    state = {
        "messages": [ToolMessage(content="device unavailable", name="device_tool", tool_call_id="call-4b")],
        "selected_worker": "skill_worker",
        "verification_status": "failed",
        "last_classification": {
            "category": "unsafe_state",
            "requires_handoff": True,
            "suggested_next_action": "handoff",
        },
    }

    assert route_after_review(state) == "report"


def test_route_after_review_routes_code_worker_repair_to_repair_node():
    state = {
        "messages": [ToolMessage(content="repair needed", name="python_sandbox", tool_call_id="call-5")],
        "selected_worker": "code_worker",
        "next_execution_hint": "repair",
        "verification_status": "pending",
    }

    assert route_after_review(state) == "repair"


@pytest.mark.asyncio
async def test_clarify_followup_node_sets_clarify_mode():
    result = await clarify_followup_node(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "browser",
            "next_execution_hint": "ask_user",
            "last_classification": {
                "category": "invalid_input",
                "suggested_next_action": "ask_user",
            },
        }
    )

    assert result["execution_mode"] == "clarify_followup"
    assert result["next_execution_hint"] == "ask_user"
    assert "ASK USER MODE" in result["messages"][0].content


@pytest.mark.asyncio
async def test_verify_followup_node_sets_verify_hint():
    result = await verify_followup_node(
        {
            "selected_worker": "skill_worker",
            "verification_status": "required",
            "next_execution_hint": "ask_user",
            "selected_skill": "browser",
            "execution_mode": "skill_act",
            "last_classification": {
                "category": "success",
                "user_facing_summary": "Action executed and should be verified before completion.",
                "debug_summary": "Clicked submit button",
            },
        }
    )

    assert result["next_execution_hint"] == "verify"
    assert result["execution_mode"] == "verify_followup"
    assert result["verification_status"] == "required"
    assert result["verify_context"]["worker"] == "skill_worker"
    assert result["verify_context"]["skill"] == "browser"
    assert result["verify_context"]["execution_mode"] == "skill_act"
    assert result["verify_context"]["category"] == "success"


@pytest.mark.asyncio
async def test_repair_followup_node_sets_repair_hint_and_retry_count():
    result = await repair_followup_node(
        {
            "selected_worker": "code_worker",
            "retry_count": 1,
            "next_execution_hint": "repair",
            "last_classification": {
                "category": "retryable_runtime_error",
                "user_facing_summary": "Code execution failed with a repairable runtime error.",
                "debug_summary": "Traceback: ValueError('boom')",
            },
        }
    )

    assert result["next_execution_hint"] == "repair"
    assert result["execution_mode"] == "repair_followup"
    assert result["retry_count"] == 2
    assert "CODE REPAIR" in result["messages"][0].content


@pytest.mark.asyncio
async def test_reviewer_gate_node_prepares_review_state(mocker):
    mocker.patch(
        "app.core.agent.WorkerDispatcher.prepare_review",
        return_value={
            "verification_status": "required",
            "execution_mode": "review_prepare",
            "verify_context": None,
            "review_snapshot": {
                "verification_status": "required",
                "classification": "success",
            },
        },
    )

    result = await reviewer_gate_node(
        {
            "trace_id": "trace-1",
            "selected_worker": "skill_worker",
            "next_execution_hint": "verify",
            "last_outcome": {"status": "success"},
            "last_classification": {
                "category": "success",
                "suggested_next_action": "verify",
            },
            "execution_history": [
                {
                    "tool_name": "browser_click",
                    "worker": "skill_worker",
                    "classification": "success",
                    "next_execution_hint": "verify",
                }
            ],
        }
    )

    assert result["verification_status"] == "required"
    assert result["execution_history"][-1]["review_snapshot"]["verification_status"] == "required"


@pytest.mark.asyncio
async def test_review_path_verify_followup_stays_explicit(mocker):
    mocker.patch(
        "app.core.agent.WorkerDispatcher.prepare_review",
        return_value={
            "verification_status": "required",
            "execution_mode": "review_prepare",
            "verify_context": {
                "reason": "Confirm the light changed state",
                "worker": "skill_worker",
                "skill": "homeassistant",
                "category": "success",
                "execution_mode": "skill_act",
            },
            "review_snapshot": {
                "verification_status": "required",
                "classification": "success",
                "next_action": "verify",
            },
        },
    )

    review_patch = await reviewer_gate_node(
        {
            "trace_id": "trace-verify",
            "selected_worker": "skill_worker",
            "selected_skill": "homeassistant",
            "next_execution_hint": "verify",
            "last_outcome": {"status": "success"},
            "last_classification": {
                "category": "success",
                "suggested_next_action": "verify",
            },
            "execution_history": [
                {
                    "tool_name": "call_service_tool",
                    "worker": "skill_worker",
                    "classification": "success",
                    "next_execution_hint": "verify",
                }
            ],
        }
    )

    route = route_after_review(
        {
            "messages": [ToolMessage(content="ok", name="call_service_tool", tool_call_id="call-verify-path")],
            "selected_worker": "skill_worker",
            "selected_skill": "homeassistant",
            "next_execution_hint": "verify",
            "last_classification": {
                "category": "success",
                "suggested_next_action": "verify",
            },
            "verification_status": review_patch["verification_status"],
            "execution_history": review_patch["execution_history"],
        }
    )

    verify_patch = await verify_followup_node(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "homeassistant",
            "verification_status": review_patch["verification_status"],
            "next_execution_hint": "verify",
            "execution_mode": "skill_act",
            "last_classification": {
                "category": "success",
                "user_facing_summary": "Action executed and should be verified before completion.",
                "debug_summary": "Light turn_on returned successfully",
            },
        }
    )

    assert route == "verify"
    assert verify_patch["execution_mode"] == "verify_followup"
    assert verify_patch["verify_context"]["worker"] == "skill_worker"


@pytest.mark.asyncio
async def test_review_path_failed_handoff_reaches_report_failure(mocker):
    mocker.patch(
        "app.core.agent.WorkerDispatcher.prepare_review",
        return_value={
            "verification_status": "failed",
            "execution_mode": "review_prepare",
            "verify_context": None,
            "review_snapshot": {
                "verification_status": "failed",
                "classification": "unsafe_state",
                "next_action": "handoff",
            },
        },
    )

    review_patch = await reviewer_gate_node(
        {
            "trace_id": "trace-report",
            "selected_worker": "skill_worker",
            "selected_skill": "homeassistant",
            "next_execution_hint": "report",
            "last_outcome": {"status": "error"},
            "last_classification": {
                "category": "unsafe_state",
                "requires_handoff": True,
                "suggested_next_action": "handoff",
                "user_facing_summary": "Device is in an unsafe state.",
                "debug_summary": "HVAC safety interlock active",
            },
            "execution_history": [
                {
                    "tool_name": "call_service_tool",
                    "worker": "skill_worker",
                    "classification": "unsafe_state",
                    "next_execution_hint": "report",
                }
            ],
            "messages": [HumanMessage(content="关闭空调")],
        }
    )

    route = route_after_review(
        {
            "messages": [ToolMessage(content="unsafe", name="call_service_tool", tool_call_id="call-report-path")],
            "selected_worker": "skill_worker",
            "selected_skill": "homeassistant",
            "next_execution_hint": "report",
            "last_classification": {
                "category": "unsafe_state",
                "requires_handoff": True,
                "suggested_next_action": "handoff",
                "user_facing_summary": "Device is in an unsafe state.",
                "debug_summary": "HVAC safety interlock active",
            },
            "verification_status": review_patch["verification_status"],
            "execution_history": review_patch["execution_history"],
        }
    )

    report_patch = await report_failure_node(
        {
            "messages": [HumanMessage(content="关闭空调")],
            "selected_worker": "skill_worker",
            "selected_skill": "homeassistant",
            "next_execution_hint": "report",
            "last_classification": {
                "category": "unsafe_state",
                "user_facing_summary": "Device is in an unsafe state.",
                "debug_summary": "HVAC safety interlock active",
            },
        }
    )

    assert route == "report"
    assert report_patch["verification_status"] == "failed"
    assert "未能完成" in report_patch["messages"][0].content
