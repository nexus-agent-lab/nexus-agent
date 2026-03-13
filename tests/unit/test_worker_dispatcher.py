from unittest.mock import patch

import pytest

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
    assert patch_result["execution_mode"] == "skill_execute"


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
    assert patch_result["execution_mode"] == "code_execute"


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
