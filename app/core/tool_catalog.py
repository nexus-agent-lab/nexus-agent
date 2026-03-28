from __future__ import annotations

from typing import Any

from app.core.tool_metadata import get_tool_metadata
from app.core.tool_router import CORE_TOOL_NAMES


class ToolCatalog:
    """Centralizes graph-facing tool selection and worker-aware filtering."""

    def __init__(self, tools: list[Any]):
        self.tools = tools or []

    @staticmethod
    def dedupe_by_name(tool_list: list[Any]) -> list[Any]:
        unique = {}
        for tool in tool_list or []:
            unique[getattr(tool, "name", str(tool))] = tool
        return list(unique.values())

    def core_tools(self) -> list[Any]:
        return [tool for tool in self.tools if getattr(tool, "name", "") in CORE_TOOL_NAMES]

    def tools_by_names(self, tool_names: list[str]) -> list[Any]:
        if not tool_names:
            return []

        wanted = set(tool_names)
        return [tool for tool in self.tools if getattr(tool, "name", "") in wanted]

    @staticmethod
    def required_tool_names_for_skills(matched_skills: list[dict]) -> list[str]:
        required_names = []
        for skill in matched_skills or []:
            metadata = skill.get("metadata", {}) or {}
            for tool_name in metadata.get("required_tools", []) or []:
                if tool_name not in required_names:
                    required_names.append(tool_name)
        return required_names

    def filter_for_worker(self, selected_worker: str | None, matched_skills: list[dict]) -> list[Any]:
        """
        Conservative worker-aware tool filtering for the current migration phase.

        This should remain a centralized compatibility layer until dedicated
        worker subgraphs own tool selection directly.
        """
        current_tools = self.tools
        if not current_tools or not selected_worker:
            return current_tools

        core_tools = self.core_tools()
        skill_tools = self.tools_by_names(self.required_tool_names_for_skills(matched_skills))
        if selected_worker == "code_worker":
            filtered = [
                tool
                for tool in current_tools
                if getattr(tool, "name", "") in CORE_TOOL_NAMES or getattr(tool, "name", "") == "python_sandbox"
            ]
            return self.dedupe_by_name(filtered or current_tools)

        if selected_worker == "skill_worker" and skill_tools:
            return self.dedupe_by_name(core_tools + skill_tools)

        if selected_worker == "research_worker":
            filtered = []
            for tool in current_tools:
                metadata = get_tool_metadata(tool)
                operation_kind = metadata.get("operation_kind")
                if getattr(tool, "name", "") in CORE_TOOL_NAMES and getattr(tool, "name", "") != "python_sandbox":
                    filtered.append(tool)
                elif not metadata.get("side_effect", False) and operation_kind in {"discover", "read", "verify"}:
                    filtered.append(tool)
            return self.dedupe_by_name(filtered or current_tools)

        return current_tools
