from types import SimpleNamespace

from app.core.tool_catalog import ToolCatalog
from app.core.worker_graphs.code_worker import prepare_code_worker_tools
from app.core.worker_graphs.skill_worker import prepare_skill_worker_tools


def _tool(name: str, metadata: dict | None = None):
    return SimpleNamespace(name=name, metadata=metadata or {}, description=name)


def test_tool_catalog_filters_code_worker_to_code_and_core_tools():
    catalog = ToolCatalog(
        [
            _tool("python_sandbox", {"preferred_worker": "code_worker"}),
            _tool("get_current_time", {"preferred_worker": "chat_worker"}),
            _tool("call_service_tool", {"preferred_worker": "skill_worker"}),
        ]
    )

    filtered = catalog.filter_for_worker("code_worker", matched_skills=[])
    names = [tool.name for tool in filtered]

    assert "python_sandbox" in names
    assert "get_current_time" in names
    assert "call_service_tool" not in names


def test_tool_catalog_filters_skill_worker_to_required_skill_tools():
    catalog = ToolCatalog(
        [
            _tool("get_current_time"),
            _tool("list_entities"),
            _tool("call_service_tool"),
            _tool("python_sandbox"),
        ]
    )

    filtered = catalog.filter_for_worker(
        "skill_worker",
        matched_skills=[
            {
                "name": "homeassistant",
                "metadata": {"required_tools": ["list_entities", "call_service_tool"]},
            }
        ],
    )
    names = [tool.name for tool in filtered]

    assert "list_entities" in names
    assert "call_service_tool" in names
    assert "get_current_time" in names


def test_tool_catalog_filters_research_worker_to_low_side_effect_tools():
    catalog = ToolCatalog(
        [
            _tool("get_current_time"),
            _tool("browser_extract", {"operation_kind": "read", "side_effect": False}),
            _tool("call_service_tool", {"operation_kind": "act", "side_effect": True}),
        ]
    )

    filtered = catalog.filter_for_worker("research_worker", matched_skills=[])
    names = [tool.name for tool in filtered]

    assert "browser_extract" in names
    assert "get_current_time" in names
    assert "call_service_tool" not in names


def test_skill_worker_prepare_prefers_discovery_tools_for_skill_discovery():
    tools = [
        _tool("get_current_time"),
        _tool("list_entities", {"operation_kind": "discover", "side_effect": False}),
        _tool("read_entity_state", {"operation_kind": "read", "side_effect": False}),
        _tool("call_service_tool", {"operation_kind": "act", "side_effect": True}),
    ]

    filtered = prepare_skill_worker_tools(
        {"selected_worker": "skill_worker", "intent_class": "skill_discovery"},
        tools,
        matched_skills=[],
    )
    names = [tool.name for tool in filtered]

    assert "list_entities" in names
    assert "read_entity_state" in names
    assert "call_service_tool" not in names


def test_skill_worker_prepare_prefers_verify_and_read_tools():
    tools = [
        _tool("get_current_time"),
        _tool("check_device_state", {"operation_kind": "verify", "side_effect": False}),
        _tool("read_entity_state", {"operation_kind": "read", "side_effect": False}),
        _tool("turn_on_light", {"operation_kind": "act", "side_effect": True}),
    ]

    filtered = prepare_skill_worker_tools(
        {
            "selected_worker": "skill_worker",
            "last_classification": {"suggested_next_action": "verify"},
        },
        tools,
        matched_skills=[],
    )
    names = [tool.name for tool in filtered]

    assert "check_device_state" in names
    assert "read_entity_state" in names
    assert "turn_on_light" not in names


def test_skill_worker_prepare_uses_next_execution_hint_for_verify():
    tools = [
        _tool("get_current_time"),
        _tool("python_sandbox", {"preferred_worker": "code_worker"}),
        _tool("check_page_state", {"operation_kind": "verify", "side_effect": False}),
        _tool("read_page_text", {"operation_kind": "read", "side_effect": False}),
        _tool("browser_click", {"operation_kind": "act", "side_effect": True}),
    ]

    filtered = prepare_skill_worker_tools(
        {
            "selected_worker": "skill_worker",
            "next_execution_hint": "verify",
        },
        tools,
        matched_skills=[],
    )
    names = [tool.name for tool in filtered]

    assert "check_page_state" in names
    assert "read_page_text" in names
    assert "browser_click" not in names
    assert "python_sandbox" not in names


def test_skill_worker_prepare_uses_next_execution_hint_for_discovery():
    tools = [
        _tool("get_current_time"),
        _tool("list_tabs", {"operation_kind": "discover", "side_effect": False}),
        _tool("read_tab", {"operation_kind": "read", "side_effect": False}),
        _tool("close_tab", {"operation_kind": "act", "side_effect": True}),
    ]

    filtered = prepare_skill_worker_tools(
        {
            "selected_worker": "skill_worker",
            "next_execution_hint": "discover",
        },
        tools,
        matched_skills=[],
    )
    names = [tool.name for tool in filtered]

    assert "list_tabs" in names
    assert "read_tab" in names
    assert "close_tab" not in names


def test_skill_worker_prepare_uses_next_execution_hint_for_ask_user():
    tools = [
        _tool("get_current_time"),
        _tool("list_tabs", {"operation_kind": "discover", "side_effect": False}),
        _tool("browser_click", {"operation_kind": "act", "side_effect": True}),
    ]

    filtered = prepare_skill_worker_tools(
        {
            "selected_worker": "skill_worker",
            "next_execution_hint": "ask_user",
        },
        tools,
        matched_skills=[],
    )

    assert filtered == []


def test_skill_worker_prepare_uses_next_execution_hint_for_act():
    tools = [
        _tool("get_current_time"),
        _tool("list_entities", {"operation_kind": "discover", "side_effect": False}),
        _tool("read_entity_state", {"operation_kind": "read", "side_effect": False}),
        _tool("call_service_tool", {"operation_kind": "act", "side_effect": True}),
    ]

    filtered = prepare_skill_worker_tools(
        {
            "selected_worker": "skill_worker",
            "next_execution_hint": "act",
        },
        tools,
        matched_skills=[],
    )
    names = [tool.name for tool in filtered]

    assert "call_service_tool" in names
    assert "list_entities" not in names
    assert "read_entity_state" not in names


def test_code_worker_prepare_uses_next_execution_hint_for_verify():
    tools = [
        _tool("python_sandbox", {"preferred_worker": "code_worker"}),
        _tool("get_current_time"),
        _tool("read_artifact", {"operation_kind": "read", "side_effect": False}),
        _tool("verify_result", {"operation_kind": "verify", "side_effect": False}),
    ]

    filtered = prepare_code_worker_tools(
        {
            "selected_worker": "code_worker",
            "next_execution_hint": "verify",
        },
        tools,
    )
    names = [tool.name for tool in filtered]

    assert "verify_result" in names
    assert "read_artifact" in names
    assert "python_sandbox" not in names


def test_code_worker_prepare_uses_next_execution_hint_for_report():
    tools = [
        _tool("python_sandbox", {"preferred_worker": "code_worker"}),
        _tool("get_current_time"),
    ]

    filtered = prepare_code_worker_tools(
        {
            "selected_worker": "code_worker",
            "next_execution_hint": "report",
        },
        tools,
    )

    assert filtered == []
