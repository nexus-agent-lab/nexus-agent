from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.tool_executor import build_tool_fingerprint
from app.core.worker_dispatcher import WorkerDispatcher


class DummyAuditInterceptor:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummyUser:
    def __init__(self, user_id=7, username="tester", role="user"):
        self.id = user_id
        self.username = username
        self.role = role


class DummyTool:
    def __init__(self, name="dummy_tool", metadata=None, result="ok"):
        self.name = name
        self.metadata = metadata or {}
        self.tags = ["tag:safe"]
        self._result = result

    async def ainvoke(self, args):
        return self._result


@pytest.mark.asyncio
async def test_execute_tool_call_permission_denied():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=False):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "homeassistant"},
                tool_name="dummy_tool",
                tool_call_id="call-1",
                tool_args={"entity_id": "light.kitchen"},
                tool_to_call=DummyTool(),
                user=DummyUser(),
                trace_id="trace-1",
            )

    assert patch_result["message"].name == "dummy_tool"
    assert "Permission denied" in patch_result["message"].content
    assert patch_result["outcome"]["status"] == "error"
    assert patch_result["classification"]["category"] == "permission_denied"
    assert patch_result["execution_mode"] == "skill_read"


@pytest.mark.asyncio
async def test_execute_tool_call_success():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "code_worker", "selected_skill": None, "context": "work"},
                tool_name="python_sandbox",
                tool_call_id="call-2",
                tool_args={"code": "print('ok')"},
                tool_to_call=DummyTool(
                    name="python_sandbox", metadata={"preferred_worker": "code_worker"}, result="ok"
                ),
                user=DummyUser(),
                trace_id="trace-2",
            )

    assert patch_result["message"].name == "python_sandbox"
    assert patch_result["message"].content == "ok"
    assert patch_result["outcome"]["status"] == "success"
    assert patch_result["classification"]["category"] == "success"
    assert patch_result["classification"]["suggested_next_action"] == "verify"
    assert patch_result["execution_mode"] == "code_execute"
    assert patch_result["next_execution_hint"] == "verify"


@pytest.mark.asyncio
async def test_execute_tool_call_classifies_python_sandbox_text_errors():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "code_worker", "selected_skill": None, "context": "work"},
                tool_name="python_sandbox",
                tool_call_id="call-3",
                tool_args={"code": "raise ValueError('boom')"},
                tool_to_call=DummyTool(
                    name="python_sandbox",
                    metadata={"preferred_worker": "code_worker", "capability_domain": "code_execution"},
                    result="Execution Error:\nTraceback (most recent call last):\nValueError: boom",
                ),
                user=DummyUser(),
                trace_id="trace-3",
            )

    assert patch_result["outcome"]["status"] == "success"
    assert patch_result["classification"]["category"] == "retryable_runtime_error"
    assert patch_result["classification"]["suggested_next_action"] == "retry_same_worker"
    assert patch_result["execution_mode"] == "code_execute"
    assert patch_result["next_execution_hint"] == "repair"


@pytest.mark.asyncio
async def test_execute_tool_call_blocks_repeated_code_fingerprint():
    fingerprint = build_tool_fingerprint(
        "python_sandbox",
        args={"code": "raise ValueError('boom')"},
        selected_skill=None,
    )

    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {
                    "selected_worker": "code_worker",
                    "selected_skill": None,
                    "context": "work",
                    "blocked_fingerprints": [fingerprint],
                },
                tool_name="python_sandbox",
                tool_call_id="call-4",
                tool_args={"code": "raise ValueError('boom')"},
                tool_to_call=DummyTool(
                    name="python_sandbox",
                    metadata={"preferred_worker": "code_worker", "capability_domain": "code_execution"},
                    result="Execution Error:\nTraceback (most recent call last):\nValueError: boom",
                ),
                user=DummyUser(),
                trace_id="trace-4",
            )

    assert patch_result["message"] is None
    assert patch_result["classification"]["category"] == "non_retryable_runtime_error"
    assert patch_result["classification"]["requires_handoff"] is True
    assert patch_result["execution_mode"] == "code_blocked"
    assert patch_result["next_execution_hint"] == "report"


@pytest.mark.asyncio
async def test_skill_worker_dispatch_marks_discovery_tools():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "web_browsing"},
                tool_name="list_available_tools",
                tool_call_id="call-5",
                tool_args={},
                tool_to_call=DummyTool(
                    name="list_available_tools",
                    metadata={"preferred_worker": "skill_worker", "operation_kind": "discover"},
                    result="[]",
                ),
                user=DummyUser(),
                trace_id="trace-5",
            )

    assert patch_result["execution_mode"] == "skill_discover"


@pytest.mark.asyncio
async def test_skill_worker_dispatch_marks_action_tools():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "homeassistant"},
                tool_name="watch_entity",
                tool_call_id="call-6",
                tool_args={"entity_id": "light.kitchen"},
                tool_to_call=DummyTool(
                    name="watch_entity",
                    metadata={"preferred_worker": "skill_worker", "operation_kind": "act"},
                    result="ok",
                ),
                user=DummyUser(),
                trace_id="trace-6",
            )

    assert patch_result["execution_mode"] == "skill_act"


@pytest.mark.asyncio
async def test_prepare_tools_preserves_next_execution_hint_in_decision():
    tools, decision = await WorkerDispatcher.prepare_tools(
        {
            "selected_worker": "code_worker",
            "next_execution_hint": "verify",
            "verify_context": {"reason": "Confirm output correctness"},
        },
        [
            DummyTool(name="python_sandbox", metadata={"preferred_worker": "code_worker"}),
            DummyTool(name="verify_result", metadata={"operation_kind": "verify", "side_effect": False}),
        ],
        matched_skills=[],
    )

    assert decision["selected_worker"] == "code_worker"
    assert decision["next_execution_hint"] == "verify"
    assert decision["verify_context"]["reason"] == "Confirm output correctness"
    assert len(tools) >= 1


def test_route_after_review_prefers_explicit_followup_routes():
    route = WorkerDispatcher.route_after_review(
        {
            "selected_worker": "skill_worker",
            "verification_status": "failed",
            "next_execution_hint": "ask_user",
            "last_classification": {
                "category": "invalid_input",
                "suggested_next_action": "ask_user",
            },
        },
        fallback_route="agent",
    )

    assert route == "clarify"


def test_route_after_agent_prefers_verify_before_end():
    route = WorkerDispatcher.route_after_agent(
        {
            "verification_status": "required",
            "llm_call_count": 1,
        },
        has_tool_calls=False,
    )

    assert route == "verify"


def test_route_after_agent_routes_code_report_mode_to_report():
    route = WorkerDispatcher.route_after_agent(
        {
            "selected_worker": "code_worker",
            "next_execution_hint": "report",
            "llm_call_count": 0,
        },
        has_tool_calls=False,
    )

    assert route == "report"


def test_route_after_tool_prefers_repair_for_code_worker():
    route = WorkerDispatcher.route_after_tool(
        {
            "selected_worker": "code_worker",
            "next_execution_hint": "repair",
            "retry_count": 0,
        },
        classification_retryable=False,
        tool_error_retryable=False,
    )

    assert route == "repair"


def test_route_after_tool_uses_reflexion_for_retryable_classification():
    route = WorkerDispatcher.route_after_tool(
        {
            "selected_worker": "skill_worker",
            "retry_count": 1,
        },
        classification_retryable=True,
        tool_error_retryable=False,
    )

    assert route == "reflexion"


def test_route_after_tool_with_runtime_derives_retry_inputs_from_state():
    route, retry_state = WorkerDispatcher.route_after_tool_with_runtime(
        {
            "selected_worker": "skill_worker",
            "retry_count": 1,
            "messages": [ToolMessage(content="Execution Error: boom", name="python_sandbox", tool_call_id="call-1")],
            "last_classification": {
                "retryable": True,
                "requires_handoff": False,
            },
        }
    )

    assert route == "reflexion"
    assert retry_state["classification_retryable"] is True
    assert retry_state["tool_error_retryable"] is True


def test_route_after_review_with_runtime_uses_dispatcher_fallback_route():
    route, review_state = WorkerDispatcher.route_after_review_with_runtime(
        {
            "selected_worker": "skill_worker",
            "retry_count": 1,
            "messages": [ToolMessage(content="Execution Error: boom", name="browser_click", tool_call_id="call-2")],
            "last_classification": {
                "retryable": True,
                "requires_handoff": False,
            },
        }
    )

    assert route == "reflexion"
    assert review_state["fallback_route"] == "reflexion"
    assert review_state["classification_retryable"] is True
    assert review_state["tool_error_retryable"] is True


def test_build_followup_instructions_for_code_verify_report_flow():
    instructions = WorkerDispatcher.build_followup_instructions(
        {
            "selected_worker": "code_worker",
            "next_execution_hint": "report",
            "verification_status": "failed",
        }
    )

    assert any("VERIFICATION FAILED" in item for item in instructions)
    assert any("CODE REPORT MODE" in item for item in instructions)


def test_build_followup_instructions_include_verify_context():
    instructions = WorkerDispatcher.build_followup_instructions(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "browser",
            "verification_status": "required",
            "verify_context": {
                "reason": "Confirm the button click changed page state",
                "worker": "skill_worker",
                "skill": "browser",
                "detail": "Clicked submit button",
            },
        }
    )

    assert any("VERIFICATION REQUIRED" in item for item in instructions)
    assert any("Confirm the button click changed page state" in item for item in instructions)


def test_build_report_message_prefers_user_language():
    message = WorkerDispatcher.build_report_message(
        {
            "messages": [HumanMessage(content="帮我看看为什么失败了")],
            "last_classification": {
                "user_facing_summary": "执行失败",
                "debug_summary": "Traceback: boom",
            },
        }
    )

    assert "本次执行未能完成" in message
    assert "Traceback: boom" in message


def test_build_verify_context_normalizes_latest_state():
    context = WorkerDispatcher.build_verify_context(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "browser",
            "execution_mode": "skill_act",
            "next_execution_hint": "verify",
            "last_classification": {
                "category": "success",
                "user_facing_summary": "Action executed and should be verified before completion.",
                "debug_summary": "Clicked submit button",
            },
        }
    )

    assert context["worker"] == "skill_worker"
    assert context["skill"] == "browser"
    assert context["execution_mode"] == "skill_act"
    assert context["previous_hint"] == "verify"


def test_build_execution_history_entry_captures_normalized_fields():
    entry = WorkerDispatcher.build_execution_history_entry(
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


def test_annotate_execution_history_entry_adds_review_state():
    updated = WorkerDispatcher.annotate_execution_history_entry(
        {
            "tool_name": "browser_click",
            "worker": "skill_worker",
            "classification": "success",
            "next_execution_hint": "verify",
        },
        review_decision={
            "verification_status": "required",
            "execution_mode": "review_prepare",
            "verify_context": {"reason": "Confirm the button click changed page state"},
            "review_snapshot": {"verification_status": "required"},
        },
        next_execution_hint="verify",
    )

    assert updated["verification_status"] == "required"
    assert updated["review_mode"] == "review_prepare"
    assert updated["verify_reason"] == "Confirm the button click changed page state"
    assert updated["review_snapshot"]["verification_status"] == "required"


def test_build_execution_history_lesson_uses_latest_normalized_entry():
    lesson = WorkerDispatcher.build_execution_history_lesson(
        {
            "messages": [HumanMessage(content="帮我修一下这个 Python 错误")],
            "execution_history": [
                {
                    "worker": "code_worker",
                    "tool_name": "python_sandbox",
                    "classification": "retryable_runtime_error",
                    "next_execution_hint": "repair",
                    "verification_status": "pending",
                    "review_snapshot": {
                        "next_action": "retry_same_worker",
                        "verify_reason": "Confirm the repaired code produces the expected output",
                    },
                }
            ],
        }
    )

    assert lesson is not None
    assert "worker=code_worker" in lesson
    assert "tool=python_sandbox" in lesson
    assert "classification=retryable_runtime_error" in lesson
    assert "verification=pending" in lesson
    assert "review_next_action=retry_same_worker" in lesson
    assert "Reviewer note: Confirm the repaired code produces the expected output" in lesson


def test_build_code_repair_message_uses_latest_failure_context():
    message = WorkerDispatcher.build_code_repair_message(
        {
            "last_classification": {
                "user_facing_summary": "Code execution failed with a repairable runtime error.",
                "debug_summary": "Traceback: ValueError('boom')",
            }
        },
        retry_count=2,
    )

    assert "CODE REPAIR (Attempt 2/3)" in message
    assert "Traceback: ValueError('boom')" in message


def test_build_experience_replay_lesson_prefers_search_detours():
    lesson = WorkerDispatcher.build_experience_replay_lesson(
        {
            "messages": [HumanMessage(content="帮我找一下可用实体")],
            "search_count": 1,
            "retry_count": 0,
        }
    )

    assert lesson is not None
    assert "required additional tool searching" in lesson


def test_prepare_experience_replay_returns_persistable_payload():
    payload = WorkerDispatcher.prepare_experience_replay(
        {
            "messages": [
                HumanMessage(content="帮我修一下这个 Python 错误"),
                AIMessage(content="已经完成处理"),
            ],
            "user": DummyUser(),
            "execution_history": [
                {
                    "worker": "code_worker",
                    "tool_name": "python_sandbox",
                    "classification": "retryable_runtime_error",
                    "next_execution_hint": "repair",
                    "verification_status": "pending",
                }
            ],
        }
    )

    assert payload is not None
    assert payload["user_id"] == 7
    assert payload["memory_type"] == "preference"
    assert "worker=code_worker" in payload["lesson"]


def test_prepare_experience_replay_skips_when_latest_message_is_not_ai():
    payload = WorkerDispatcher.prepare_experience_replay(
        {
            "messages": [HumanMessage(content="帮我修一下这个 Python 错误")],
            "user": DummyUser(),
        }
    )

    assert payload is None


def test_build_review_snapshot_captures_runtime_review_summary():
    snapshot = WorkerDispatcher.build_review_snapshot(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "browser",
            "execution_mode": "skill_act",
            "next_execution_hint": "verify",
            "last_classification": {
                "category": "success",
                "suggested_next_action": "verify",
                "requires_handoff": False,
            },
        },
        verification_status="required",
        execution_mode="review_prepare",
        verify_context={"reason": "Confirm the button click changed page state"},
    )

    assert snapshot["worker"] == "skill_worker"
    assert snapshot["skill"] == "browser"
    assert snapshot["verification_status"] == "required"
    assert snapshot["classification"] == "success"
    assert snapshot["verify_reason"] == "Confirm the button click changed page state"


def test_build_repair_followup_patch_sets_expected_fields():
    patch = WorkerDispatcher.build_repair_followup_patch(
        {
            "last_classification": {
                "user_facing_summary": "Code execution failed with a repairable runtime error.",
                "debug_summary": "Traceback: ValueError('boom')",
            }
        },
        retry_count=2,
    )

    assert patch["execution_mode"] == "repair_followup"
    assert patch["next_execution_hint"] == "repair"
    assert patch["retry_count"] == 2
    assert "CODE REPAIR (Attempt 2/3)" in patch["messages"][0].content


def test_should_retry_tool_error_blocks_permission_failures():
    assert WorkerDispatcher.should_retry_tool_error("Permission denied") is False
    assert WorkerDispatcher.should_retry_tool_error("Execution Error: boom") is True


def test_should_retry_classification_respects_handoff_and_retryable_states():
    assert (
        WorkerDispatcher.should_retry_classification(
            {
                "last_classification": {
                    "retryable": True,
                    "requires_handoff": False,
                }
            }
        )
        is True
    )
    assert (
        WorkerDispatcher.should_retry_classification(
            {
                "selected_worker": "code_worker",
                "attempts_by_worker": {"code_worker": 3},
                "last_classification": {
                    "retryable": True,
                    "requires_handoff": False,
                },
            }
        )
        is False
    )


def test_build_reflexion_message_uses_latest_failure_sources():
    critique, failures = WorkerDispatcher.build_reflexion_message(
        {
            "messages": [ToolMessage(content="Execution Error", name="python_sandbox", tool_call_id="call-1")],
            "last_classification": {
                "debug_summary": "Traceback: ValueError('boom')",
            },
        },
        retry_count=2,
    )

    assert "REFLECTION (Attempt 2/3)" in critique
    assert "Traceback: ValueError('boom')" in critique
    assert failures


def test_build_reflexion_patch_sets_retry_state_and_message():
    patch, failures = WorkerDispatcher.build_reflexion_patch(
        {
            "messages": [ToolMessage(content="Execution Error", name="python_sandbox", tool_call_id="call-2")],
            "last_classification": {
                "debug_summary": "Traceback: ValueError('boom')",
            },
        },
        retry_count=2,
    )

    assert patch["retry_count"] == 2
    assert "REFLECTION (Attempt 2/3)" in patch["messages"][0].content
    assert patch["reflexions"]
    assert failures


def test_build_verify_followup_patch_sets_verify_state():
    patch = WorkerDispatcher.build_verify_followup_patch(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "browser",
            "execution_mode": "skill_act",
            "last_classification": {
                "category": "success",
                "user_facing_summary": "Action executed and should be verified before completion.",
            },
        }
    )

    assert patch["execution_mode"] == "verify_followup"
    assert patch["next_execution_hint"] == "verify"
    assert patch["verification_status"] == "required"
    assert patch["verify_context"]["worker"] == "skill_worker"


def test_build_clarify_followup_patch_disables_tools_and_prompts_question():
    patch = WorkerDispatcher.build_clarify_followup_patch()

    assert patch["execution_mode"] == "clarify_followup"
    assert patch["next_execution_hint"] == "ask_user"
    assert "ASK USER MODE" in patch["messages"][0].content


@pytest.mark.asyncio
async def test_prepare_review_exposes_review_snapshot():
    decision = await WorkerDispatcher.prepare_review(
        {
            "selected_worker": "skill_worker",
            "selected_skill": "browser",
            "execution_mode": "skill_act",
            "next_execution_hint": "verify",
            "last_classification": {
                "category": "success",
                "suggested_next_action": "verify",
                "requires_handoff": False,
            },
        }
    )

    assert decision["verification_status"] == "required"
    assert decision["review_snapshot"]["worker"] == "skill_worker"
    assert decision["review_snapshot"]["classification"] == "success"


@pytest.mark.asyncio
async def test_skill_worker_action_requests_verification_for_side_effects():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "browser"},
                tool_name="browser_click",
                tool_call_id="call-7",
                tool_args={"selector": "#submit"},
                tool_to_call=DummyTool(
                    name="browser_click",
                    metadata={
                        "preferred_worker": "skill_worker",
                        "operation_kind": "act",
                        "side_effect": True,
                    },
                    result="clicked",
                ),
                user=DummyUser(),
                trace_id="trace-7",
            )

    assert patch_result["classification"]["category"] == "success"
    assert patch_result["classification"]["suggested_next_action"] == "verify"
    assert patch_result["execution_mode"] == "skill_act"
    assert patch_result["next_execution_hint"] == "verify"


@pytest.mark.asyncio
async def test_skill_worker_discovery_does_not_loop_into_more_discovery():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "homeassistant"},
                tool_name="find_entity",
                tool_call_id="call-8",
                tool_args={"name": "bedroom lamp"},
                tool_to_call=DummyTool(
                    name="find_entity",
                    metadata={"preferred_worker": "skill_worker", "operation_kind": "discover"},
                    result="entity not found",
                ),
                user=DummyUser(),
                trace_id="trace-8",
            )

    assert patch_result["classification"]["category"] == "invalid_input"
    assert patch_result["classification"]["suggested_next_action"] == "ask_user"
    assert patch_result["execution_mode"] == "skill_discover"
    assert patch_result["next_execution_hint"] == "ask_user"


@pytest.mark.asyncio
async def test_skill_worker_requires_handoff_marks_report_followup():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "browser"},
                tool_name="browser_click",
                tool_call_id="call-8",
                tool_args={"selector": "#dangerous"},
                tool_to_call=DummyTool(
                    name="browser_click",
                    metadata={
                        "preferred_worker": "skill_worker",
                        "operation_kind": "act",
                        "side_effect": True,
                    },
                    result="unsafe state encountered",
                ),
                user=DummyUser(),
                trace_id="trace-8",
            )

    assert patch_result["classification"]["requires_handoff"] is True
    assert patch_result["classification"]["suggested_next_action"] == "handoff"
    assert patch_result["next_execution_hint"] == "report"


@pytest.mark.asyncio
async def test_skill_worker_verify_invalid_input_marks_verification_failed():
    with patch("app.core.worker_graphs.shared_execution.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_graphs.shared_execution.AuditInterceptor", DummyAuditInterceptor):
            patch_result = await WorkerDispatcher.execute_tool_call(
                {"selected_worker": "skill_worker", "selected_skill": "browser"},
                tool_name="browser_verify_text",
                tool_call_id="call-9",
                tool_args={"selector": "#status"},
                tool_to_call=DummyTool(
                    name="browser_verify_text",
                    metadata={"preferred_worker": "skill_worker", "operation_kind": "verify"},
                    result="not found",
                ),
                user=DummyUser(),
                trace_id="trace-9",
            )

    assert patch_result["classification"]["category"] == "verification_failed"
    assert patch_result["classification"]["suggested_next_action"] == "ask_user"
    assert patch_result["execution_mode"] == "skill_verify"
    assert patch_result["next_execution_hint"] == "report"
