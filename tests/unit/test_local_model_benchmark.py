from app.benchmarks.evaluators import evaluate_attempt
from app.benchmarks.models import AttemptMetrics, AttemptResult, ScenarioDefinition
from app.benchmarks.runner import BenchmarkRunner, default_suite_dir
from app.benchmarks.scoring import build_summary, normalize_speed


def test_load_manifest_and_scenarios():
    runner = BenchmarkRunner(
        suite_dir=default_suite_dir(),
        output_dir="benchmark_results_test",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )
    manifest = runner.load_manifest()
    scenarios = runner.load_scenarios(manifest)

    assert manifest.suite_id == "nexus_local_models_v1"
    assert len(scenarios) == 5
    assert scenarios[0].id == "task_01_tool_call"


def test_runner_detects_ollama_and_local_execution_metadata():
    runner = BenchmarkRunner(
        suite_dir=default_suite_dir(),
        output_dir="benchmark_results_test",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )

    environment = runner._environment()

    assert runner.ollama_url == "http://localhost:11434"
    assert environment["execution_mode"] == "local_direct"
    assert environment["uses_docker"] is False
    assert environment["serial_model_execution"] is True
    assert environment["warmup_before_measurement"] is True


def test_evaluate_attempt_scores_tool_and_response_quality():
    scenario = ScenarioDefinition.model_validate_json((default_suite_dir() / "task_01_tool_call.json").read_text())
    result = evaluate_attempt(
        scenario=scenario,
        tool_names=["fixture_get_weather"],
        final_response="Shanghai is 22C and cloudy.",
        format_error_count=0,
        retry_count=0,
    )

    assert result["success"] is True
    assert result["correct_tool_selection"] is True
    assert result["grounded_response"] is True
    assert result["wrong_tool_count"] == 0


def test_build_summary_prefers_tool_selection_and_grounding():
    attempt = AttemptResult(
        benchmark_id="bench-1",
        suite_id="suite-1",
        suite_version=1,
        model="glm4.7-flash",
        task_id="task-1",
        repetition=1,
        started_at="2026-03-25T00:00:00Z",
        completed_at="2026-03-25T00:00:03Z",
        prompt_hash="a",
        conversation_hash="b",
        final_response="Shanghai is 22C and cloudy.",
        tool_calls=[],
        metrics=AttemptMetrics(
            success=True,
            total_completion_time=3.0,
            tokens_per_second=10.0,
            correct_tool_selection=True,
            grounded_response=True,
            complete_response=True,
            format_error_count=0,
            hallucination=False,
            retry_count=0,
            wrong_tool_count=0,
            unnecessary_tool_call_count=0,
        ),
        metadata={"ideal_tool_order": []},
    )

    summary = build_summary(
        benchmark_id="bench-1",
        suite_id="suite-1",
        suite_version=1,
        model="glm4.7-flash",
        attempts=[attempt],
        environment={"host": "test"},
        normalized_speed=normalize_speed(10.0, 10.0),
    )

    assert summary.final_score > 0.9
    assert summary.tool_effectiveness.correct_tool_selection_rate == 1.0
    assert summary.response_quality.grounded_response_rate == 1.0
