from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

WEATHER_DATA = {
    "shanghai": "Shanghai is 22C and cloudy.",
    "beijing": "Beijing is 18C and sunny.",
}

FILE_DATA = {
    "docs/benchmark_notes.txt": "Release version: 2.4.1\nOwner: Nexus Team\n",
    "reports/q1.txt": "Q1 revenue: 120\nQ1 cost: 45\n",
}

SEARCH_DATA = {
    "release window for project atlas": "Project Atlas release window is 2026-04-12.",
    "benchmark policy": "The benchmark policy requires one standardized benchmark suite for all models.",
    "nexus agent deployment checklist": "Deployment checklist: validate config, verify auth, run smoke test.",
}


@dataclass
class FixtureRuntime:
    fail_once_keys: set[str] = field(default_factory=set)
    fail_counters: dict[str, int] = field(default_factory=dict)

    def should_fail_once(self, key: str) -> bool:
        if key not in self.fail_once_keys:
            return False
        count = self.fail_counters.get(key, 0)
        self.fail_counters[key] = count + 1
        return count == 0


class WeatherArgs(BaseModel):
    location: str = Field(description="The city to query weather for.")


class CalcArgs(BaseModel):
    expression: str = Field(description="A simple arithmetic expression such as 3*7.")


class ReadFileArgs(BaseModel):
    path: str = Field(description="A benchmark fixture file path.")


class SearchArgs(BaseModel):
    query: str = Field(description="A benchmark search query.")


def build_fixture_tools(runtime: FixtureRuntime) -> list[StructuredTool]:
    def fixture_get_weather(location: str) -> str:
        key = location.strip().lower()
        if key not in WEATHER_DATA:
            raise ValueError(f"Unknown location: {location}")
        return WEATHER_DATA[key]

    def fixture_calculator(expression: str) -> str:
        allowed_chars = set("0123456789+-*/(). ")
        if any(ch not in allowed_chars for ch in expression):
            raise ValueError("Expression contains unsupported characters.")
        return str(eval(expression, {"__builtins__": {}}, {}))

    def fixture_read_file(path: str) -> str:
        key = path.strip()
        if key not in FILE_DATA:
            raise FileNotFoundError(f"Fixture file not found: {path}")
        return FILE_DATA[key]

    def fixture_search(query: str) -> str:
        key = query.strip().lower()
        if runtime.should_fail_once(key):
            raise RuntimeError("Transient search backend error. Please retry.")
        if key not in SEARCH_DATA:
            raise ValueError(f"No fixture search result for query: {query}")
        return SEARCH_DATA[key]

    return [
        StructuredTool.from_function(
            func=fixture_get_weather,
            name="fixture_get_weather",
            description="Get deterministic weather data for a benchmark location.",
            args_schema=WeatherArgs,
        ),
        StructuredTool.from_function(
            func=fixture_calculator,
            name="fixture_calculator",
            description="Evaluate a simple arithmetic expression for benchmark tasks.",
            args_schema=CalcArgs,
        ),
        StructuredTool.from_function(
            func=fixture_read_file,
            name="fixture_read_file",
            description="Read a deterministic benchmark fixture file.",
            args_schema=ReadFileArgs,
        ),
        StructuredTool.from_function(
            func=fixture_search,
            name="fixture_search",
            description="Search deterministic benchmark knowledge fixtures.",
            args_schema=SearchArgs,
        ),
    ]


def select_tools(tool_names: list[str], runtime: FixtureRuntime) -> list[StructuredTool]:
    tool_map = {tool.name: tool for tool in build_fixture_tools(runtime)}
    return [tool_map[name] for name in tool_names]


def runtime_from_context(fixture_context: dict[str, Any]) -> FixtureRuntime:
    return FixtureRuntime(fail_once_keys=set(fixture_context.get("fail_once_queries", [])))
