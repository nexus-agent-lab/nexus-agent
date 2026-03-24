from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class BenchmarkDefaults(BaseModel):
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 2048
    repetitions_per_task: int = 5
    max_steps: int = 6
    timeout_seconds: int = 120


class BenchmarkModelConfig(BaseModel):
    name: str
    provider: str = "openai_compatible"
    model_id: str


class ScenarioExpectation(BaseModel):
    required_tools: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    ideal_tool_order: list[str] = Field(default_factory=list)
    expected_response_contains: list[str] = Field(default_factory=list)
    forbidden_response_contains: list[str] = Field(default_factory=list)
    max_retries: int = 2
    require_grounded_response: bool = True


class ScenarioDefinition(BaseModel):
    id: str
    name: str
    category: Literal["tool_call", "multi_tool", "multi_step", "error_recovery", "long_context"]
    description: str
    user_input: str
    available_tools: list[str]
    history: list[dict[str, str]] = Field(default_factory=list)
    expectations: ScenarioExpectation
    fixture_context: dict[str, Any] = Field(default_factory=dict)


class SuiteManifest(BaseModel):
    suite_id: str
    suite_version: int
    description: str
    defaults: BenchmarkDefaults
    tasks: list[str]
    models: list[BenchmarkModelConfig] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: Literal["success", "error"]
    output: str | None = None
    error: str | None = None


class AttemptMetrics(BaseModel):
    success: bool
    total_completion_time: float
    tokens_per_second: float = 0.0
    correct_tool_selection: bool = False
    grounded_response: bool = False
    complete_response: bool = False
    format_error_count: int = 0
    hallucination: bool = False
    retry_count: int = 0
    wrong_tool_count: int = 0
    unnecessary_tool_call_count: int = 0


class AttemptResult(BaseModel):
    benchmark_id: str
    suite_id: str
    suite_version: int
    model: str
    task_id: str
    repetition: int
    started_at: datetime
    completed_at: datetime
    prompt_hash: str
    conversation_hash: str
    final_response: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    metrics: AttemptMetrics
    metadata: dict[str, Any] = Field(default_factory=dict)


class SummarySpeed(BaseModel):
    tokens_per_second: float
    avg_latency: float
    total_completion_time: float


class ToolEffectivenessSummary(BaseModel):
    correct_tool_selection_rate: float
    wrong_tool_selection_rate: float
    unnecessary_tool_call_rate: float
    tool_order_correctness_rate: float


class ResponseQualitySummary(BaseModel):
    grounded_response_rate: float
    complete_response_rate: float
    response_deviation_rate: float


class AccuracySummary(BaseModel):
    success_rate: float
    format_error_rate: float
    hallucination_rate: float


class StabilitySummary(BaseModel):
    avg_retry: float


class BenchmarkSummary(BaseModel):
    suite_id: str
    suite_version: int
    benchmark_id: str
    model: str
    environment: dict[str, Any]
    speed: SummarySpeed
    tool_effectiveness: ToolEffectivenessSummary
    response_quality: ResponseQualitySummary
    accuracy: AccuracySummary
    stability: StabilitySummary
    final_score: float
    score_formula_version: str = "v1"
