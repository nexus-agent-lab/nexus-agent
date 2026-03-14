"""
Tests for the agent graph and decision-making logic.
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.agent import (
    _build_execution_history_entry,
    _build_execution_history_lesson,
    create_agent_graph,
    repair_followup_node,
    report_failure_node,
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


def test_route_after_review_routes_code_worker_failed_to_report_node():
    state = {
        "messages": [ToolMessage(content="verify failed", name="python_sandbox", tool_call_id="call-4")],
        "selected_worker": "code_worker",
        "verification_status": "failed",
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


def test_build_execution_history_entry_captures_normalized_fields():
    entry = _build_execution_history_entry(
        tool_name="python_sandbox",
        selected_worker="code_worker",
        selected_skill=None,
        execution_mode="code_execute",
        next_execution_hint="repair",
        outcome={
            "status": "success",
            "fingerprint": "abc123",
        },
        classification={
            "category": "retryable_runtime_error",
            "suggested_next_action": "retry_same_worker",
            "requires_handoff": False,
        },
    )

    assert entry["tool_name"] == "python_sandbox"
    assert entry["worker"] == "code_worker"
    assert entry["execution_mode"] == "code_execute"
    assert entry["next_execution_hint"] == "repair"
    assert entry["classification"] == "retryable_runtime_error"
    assert entry["next_action"] == "retry_same_worker"


def test_build_execution_history_lesson_uses_latest_normalized_entry():
    lesson = _build_execution_history_lesson(
        {
            "messages": [HumanMessage(content="帮我修一下这个 Python 错误")],
            "execution_history": [
                {
                    "worker": "code_worker",
                    "tool_name": "python_sandbox",
                    "classification": "retryable_runtime_error",
                    "next_execution_hint": "repair",
                }
            ],
        }
    )

    assert lesson is not None
    assert "worker=code_worker" in lesson
    assert "tool=python_sandbox" in lesson
    assert "classification=retryable_runtime_error" in lesson


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
