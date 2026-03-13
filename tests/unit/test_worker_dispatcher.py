import pytest
from unittest.mock import patch

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
    with patch("app.core.worker_dispatcher.AuthService.check_tool_permission", return_value=False):
        with patch("app.core.worker_dispatcher.AuditInterceptor", DummyAuditInterceptor):
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


@pytest.mark.asyncio
async def test_execute_tool_call_success():
    with patch("app.core.worker_dispatcher.AuthService.check_tool_permission", return_value=True):
        with patch("app.core.worker_dispatcher.AuditInterceptor", DummyAuditInterceptor):
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
