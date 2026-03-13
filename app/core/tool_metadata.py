from __future__ import annotations

from typing import Any, Literal, TypedDict

CAPABILITY_DOMAINS = {
    "home_automation",
    "code_execution",
    "memory",
    "knowledge",
    "communication",
    "system",
    "generic",
}


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


def _infer_capability_domain(tool_name: str, metadata: dict[str, Any]) -> str:
    domain = str(
        metadata.get("capability_domain") or metadata.get("domain") or metadata.get("category") or "generic"
    ).lower()

    if tool_name == "python_sandbox":
        return "code_execution"
    if "homeassistant" in domain or "smart_home" in domain:
        return "home_automation"
    if any(token in tool_name for token in ("memory", "preference", "insight")):
        return "memory"
    if any(token in tool_name for token in ("log", "restart", "broadcast", "system")):
        return "system"
    if any(token in tool_name for token in ("browser", "search", "query", "read")):
        return "knowledge"
    return domain if domain in CAPABILITY_DOMAINS else "generic"


def _infer_operation_kind(tool_name: str, metadata: dict[str, Any]) -> str:
    operation_kind = str(metadata.get("operation_kind") or "").lower()
    if operation_kind:
        return operation_kind

    lowered_name = tool_name.lower()
    if lowered_name == "python_sandbox":
        return "transform"
    if lowered_name.startswith(("list_", "search_", "find_")):
        return "discover"
    if lowered_name.startswith(("get_", "read_", "view_", "query_")):
        return "read"
    if lowered_name.startswith(("restart_", "delete_", "remove_", "broadcast_", "call_", "watch_")):
        return "act"
    if lowered_name.startswith(("save_", "store_", "forget_", "learn_")):
        return "transform"
    if lowered_name.startswith(("verify_", "check_")):
        return "verify"
    return "read"


def _infer_preferred_worker(tool_name: str, metadata: dict[str, Any]) -> str:
    preferred_worker = str(metadata.get("preferred_worker") or "").lower()
    if preferred_worker:
        return preferred_worker

    capability_domain = _infer_capability_domain(tool_name, metadata)
    if capability_domain == "code_execution" or tool_name == "python_sandbox":
        return "code_worker"
    if capability_domain in {"home_automation", "communication"}:
        return "skill_worker"
    if capability_domain == "knowledge":
        return "research_worker"
    return "chat_worker"


def _infer_side_effect(tool_name: str, metadata: dict[str, Any]) -> bool:
    if "side_effect" in metadata:
        return bool(metadata["side_effect"])

    operation_kind = _infer_operation_kind(tool_name, metadata)
    return operation_kind in {"act", "transform", "notify"}


def _infer_risk_level(tool_name: str, metadata: dict[str, Any]) -> str:
    if metadata.get("risk_level"):
        return str(metadata["risk_level"])

    if tool_name in {"restart_system", "broadcast_notification"}:
        return "high"
    if _infer_side_effect(tool_name, metadata):
        return "medium"
    return "low"


def _infer_requires_verification(tool_name: str, metadata: dict[str, Any]) -> bool:
    if "requires_verification" in metadata:
        return bool(metadata["requires_verification"])

    capability_domain = _infer_capability_domain(tool_name, metadata)
    return _infer_side_effect(tool_name, metadata) or capability_domain in {"code_execution", "home_automation"}


def build_tool_metadata(tool_name: str, metadata: dict[str, Any] | None = None) -> ToolCapabilityMetadata:
    """
    Normalize tool metadata into the graph-facing capability contract.

    This lets the orchestration layer consume a consistent shape even when
    tools originate from different registration paths.
    """

    source_metadata = dict(metadata or {})
    normalized: ToolCapabilityMetadata = dict(DEFAULT_TOOL_METADATA)
    normalized["tool_name"] = tool_name

    if source_metadata:
        for key, value in source_metadata.items():
            if value is not None:
                normalized[key] = value

    normalized["capability_domain"] = _infer_capability_domain(tool_name, source_metadata)
    normalized["operation_kind"] = _infer_operation_kind(tool_name, source_metadata)
    normalized["preferred_worker"] = _infer_preferred_worker(tool_name, source_metadata)
    normalized["side_effect"] = _infer_side_effect(tool_name, source_metadata)
    normalized["risk_level"] = _infer_risk_level(tool_name, source_metadata)
    normalized["requires_verification"] = _infer_requires_verification(tool_name, source_metadata)

    if normalized["risk_level"] == "high":
        normalized["retry_policy"] = "never"
        normalized["max_retries"] = 0
    elif normalized["side_effect"]:
        normalized["retry_policy"] = "safe_once"
        normalized["max_retries"] = min(int(normalized.get("max_retries", 1)), 1)

    return normalized


def get_tool_metadata(tool: Any) -> ToolCapabilityMetadata:
    """Read metadata from a LangChain tool-like object and normalize it."""

    raw_metadata = getattr(tool, "metadata", None) or {}
    tool_name = getattr(tool, "name", "unknown_tool")
    return build_tool_metadata(tool_name, raw_metadata)
