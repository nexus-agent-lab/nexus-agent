from app.core.tool_metadata import build_tool_metadata


def test_tool_metadata_infers_code_worker_for_python_sandbox():
    metadata = build_tool_metadata("python_sandbox", {})

    assert metadata["capability_domain"] == "code_execution"
    assert metadata["preferred_worker"] == "code_worker"
    assert metadata["operation_kind"] == "transform"
    assert metadata["requires_verification"] is True


def test_tool_metadata_respects_explicit_metadata_over_defaults():
    metadata = build_tool_metadata(
        "browser_navigate",
        {
            "capability_domain": "knowledge",
            "preferred_worker": "skill_worker",
            "operation_kind": "act",
            "side_effect": True,
            "requires_verification": True,
        },
    )

    assert metadata["capability_domain"] == "knowledge"
    assert metadata["preferred_worker"] == "skill_worker"
    assert metadata["operation_kind"] == "act"
    assert metadata["side_effect"] is True
    assert metadata["requires_verification"] is True


def test_tool_metadata_high_risk_tools_disable_retry():
    metadata = build_tool_metadata("restart_system", {"risk_level": "high"})

    assert metadata["risk_level"] == "high"
    assert metadata["retry_policy"] == "never"
    assert metadata["max_retries"] == 0
