from __future__ import annotations

from typing import Any, Literal, TypedDict


class ToolCapabilityMetadata(TypedDict, total=False):
    """Graph-facing capability contract shared by MCP and static tools."""

    tool_name: str
    capability_domain: Literal[
        "home_automation",
        "code_execution",
        "memory",
        "knowledge",
        "communication",
        "system",
        "generic",
    ]
    operation_kind: Literal[
        "discover",
        "read",
        "act",
        "transform",
        "verify",
        "notify",
    ]
    side_effect: bool
    risk_level: Literal["low", "medium", "high"]
    retry_policy: Literal["never", "safe_once", "bounded"]
    max_retries: int
    requires_verification: bool
    supports_dry_run: bool
    preferred_worker: Literal[
        "chat_worker",
        "skill_worker",
        "code_worker",
        "research_worker",
        "reviewer_worker",
    ]
    context_tags: list[str]
    allowed_groups: list[str]
    required_role: str


DEFAULT_TOOL_METADATA: ToolCapabilityMetadata = {
    "capability_domain": "generic",
    "operation_kind": "read",
    "side_effect": False,
    "risk_level": "low",
    "retry_policy": "bounded",
    "max_retries": 1,
    "requires_verification": False,
    "supports_dry_run": False,
    "preferred_worker": "chat_worker",
    "context_tags": ["standard"],
    "allowed_groups": [],
    "required_role": "user",
}


def build_tool_metadata(tool_name: str, metadata: dict[str, Any] | None = None) -> ToolCapabilityMetadata:
    """
    Normalize tool metadata into the graph-facing capability contract.

    This lets the orchestration layer consume a consistent shape even when
    tools originate from different registration paths.
    """

    normalized: ToolCapabilityMetadata = dict(DEFAULT_TOOL_METADATA)
    normalized["tool_name"] = tool_name

    if metadata:
        for key, value in metadata.items():
            if value is not None:
                normalized[key] = value

    return normalized


def get_tool_metadata(tool: Any) -> ToolCapabilityMetadata:
    """Read metadata from a LangChain tool-like object and normalize it."""

    raw_metadata = getattr(tool, "metadata", None) or {}
    tool_name = getattr(tool, "name", "unknown_tool")
    return build_tool_metadata(tool_name, raw_metadata)
