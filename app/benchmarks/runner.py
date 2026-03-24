from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.benchmarks.evaluators import evaluate_attempt
from app.benchmarks.fixtures.tools import runtime_from_context, select_tools
from app.benchmarks.models import AttemptMetrics, AttemptResult, ScenarioDefinition, SuiteManifest, ToolCallRecord
from app.benchmarks.scoring import build_summary, normalize_speed

BENCHMARK_SYSTEM_PROMPT = """You are evaluating as Nexus Agent.
Use only the provided tools.
Prefer the smallest correct tool sequence.
Base the final answer strictly on tool outputs.
If a tool fails transiently, retry carefully.
Do not invent data or tools.
"""


class BenchmarkRunner:
    def __init__(
        self,
        *,
        suite_dir: str | Path,
        output_dir: str | Path,
        base_url: str,
        api_key: str,
    ):
        self.suite_dir = Path(suite_dir)
        self.output_dir = Path(output_dir)
        self.base_url = base_url
        self.api_key = api_key
        self.repo_root = Path(__file__).resolve().parents[2]
        self.ollama_url = self._derive_ollama_url(base_url)

    def load_manifest(self) -> SuiteManifest:
        return SuiteManifest.model_validate_json((self.suite_dir / "manifest.json").read_text())

    def load_scenarios(self, manifest: SuiteManifest) -> list[ScenarioDefinition]:
        scenarios = []
        for task_id in manifest.tasks:
            scenarios.append(ScenarioDefinition.model_validate_json((self.suite_dir / f"{task_id}.json").read_text()))
        return scenarios

    def _build_llm(self, model: str, defaults) -> ChatOpenAI:
        model_kwargs = {"top_p": defaults.top_p}
        return ChatOpenAI(
            model=model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=defaults.temperature,
            max_tokens=defaults.max_tokens,
            model_kwargs=model_kwargs,
        )

    @staticmethod
    def _derive_ollama_url(base_url: str) -> str | None:
        lowered = base_url.lower().rstrip("/")
        if "11434" not in lowered and "ollama" not in lowered:
            return None
        if lowered.endswith("/v1"):
            return base_url.rstrip("/")[:-3]
        return base_url.rstrip("/")

    def _is_ollama_backend(self) -> bool:
        return self.ollama_url is not None

    def _warmup_model(self, model: str) -> None:
        if not self._is_ollama_backend():
            return
        with httpx.Client(timeout=180.0) as client:
            client.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": "Warm up benchmark model.", "stream": False},
            )

    def _unload_model(self, model: str) -> None:
        if not self._is_ollama_backend():
            return
        with httpx.Client(timeout=20.0) as client:
            client.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
            )

    def _unload_all_loaded_models(self) -> None:
        if not self._is_ollama_backend():
            return
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(f"{self.ollama_url}/api/ps")
                response.raise_for_status()
                payload = response.json()
                for item in payload.get("models", []):
                    name = item.get("name")
                    if name:
                        self._unload_model(name)
        except Exception:
            # Benchmark fairness is improved when this succeeds, but failure should not abort the run.
            pass

    def _conversation_hash(self, scenario: ScenarioDefinition) -> tuple[str, str]:
        prompt_payload = {"user_input": scenario.user_input, "history": scenario.history}
        prompt_hash = hashlib.sha256(json.dumps(prompt_payload, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
        conversation_hash = hashlib.sha256(
            json.dumps({"scenario": scenario.model_dump(mode="json")}, ensure_ascii=True, sort_keys=True).encode()
        ).hexdigest()
        return prompt_hash, conversation_hash

    async def _run_single_attempt(
        self,
        *,
        benchmark_id: str,
        suite: SuiteManifest,
        scenario: ScenarioDefinition,
        model: str,
        repetition: int,
    ) -> AttemptResult:
        runtime = runtime_from_context(scenario.fixture_context)
        tools = select_tools(scenario.available_tools, runtime)
        llm = self._build_llm(model, suite.defaults)
        llm_with_tools = llm.bind_tools(tools)

        messages: list[Any] = [SystemMessage(content=BENCHMARK_SYSTEM_PROMPT)]
        for item in scenario.history:
            role = item["role"]
            content = item["content"]
            if role == "user":
                messages.append(HumanMessage(content=content))
            else:
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=scenario.user_input))

        tool_records: list[ToolCallRecord] = []
        format_error_count = 0
        retry_count = 0
        final_response = ""
        started_at = datetime.now(timezone.utc)
        started_perf = time.perf_counter()

        for _ in range(suite.defaults.max_steps):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if not response.tool_calls:
                final_response = response.content if isinstance(response.content, str) else str(response.content)
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("args", {})
                tool = next((item for item in tools if item.name == tool_name), None)

                if tool is None:
                    format_error_count += 1
                    tool_records.append(
                        ToolCallRecord(name=tool_name, args=tool_args, status="error", error="Tool not available.")
                    )
                    messages.append(
                        ToolMessage(
                            content="Tool not available.",
                            tool_call_id=tool_call["id"],
                            name=tool_name,
                        )
                    )
                    continue

                try:
                    output = await tool.ainvoke(tool_args)
                    tool_records.append(
                        ToolCallRecord(name=tool_name, args=tool_args, status="success", output=str(output))
                    )
                    messages.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"], name=tool_name))
                except Exception as exc:
                    error_text = str(exc)
                    tool_records.append(
                        ToolCallRecord(name=tool_name, args=tool_args, status="error", error=error_text)
                    )
                    messages.append(
                        ToolMessage(content=f"ERROR: {error_text}", tool_call_id=tool_call["id"], name=tool_name)
                    )
                    if "Transient" in error_text or "retry" in error_text.lower():
                        retry_count += 1
                    else:
                        format_error_count += 1

        completed_at = datetime.now(timezone.utc)
        total_completion_time = time.perf_counter() - started_perf
        tool_names = [record.name for record in tool_records]
        evaluation = evaluate_attempt(
            scenario=scenario,
            tool_names=tool_names,
            final_response=final_response,
            format_error_count=format_error_count,
            retry_count=retry_count,
        )

        tokens_per_second = 0.0
        usage_metadata = getattr(messages[-1], "usage_metadata", None) if messages else None
        if usage_metadata and total_completion_time > 0:
            output_tokens = usage_metadata.get("output_tokens", 0)
            tokens_per_second = output_tokens / total_completion_time

        prompt_hash, conversation_hash = self._conversation_hash(scenario)
        return AttemptResult(
            benchmark_id=benchmark_id,
            suite_id=suite.suite_id,
            suite_version=suite.suite_version,
            model=model,
            task_id=scenario.id,
            repetition=repetition,
            started_at=started_at,
            completed_at=completed_at,
            prompt_hash=prompt_hash,
            conversation_hash=conversation_hash,
            final_response=final_response,
            tool_calls=tool_records,
            metrics=AttemptMetrics(
                success=bool(evaluation["success"]),
                total_completion_time=round(total_completion_time, 4),
                tokens_per_second=round(tokens_per_second, 4),
                correct_tool_selection=bool(evaluation["correct_tool_selection"]),
                grounded_response=bool(evaluation["grounded_response"]),
                complete_response=bool(evaluation["complete_response"]),
                format_error_count=format_error_count,
                hallucination=bool(evaluation["hallucination"]),
                retry_count=retry_count,
                wrong_tool_count=int(evaluation["wrong_tool_count"]),
                unnecessary_tool_call_count=int(evaluation["unnecessary_tool_call_count"]),
            ),
            metadata={"ideal_tool_order": scenario.expectations.ideal_tool_order},
        )

    def _environment(self) -> dict[str, Any]:
        git_sha = "unknown"
        try:
            git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo_root, text=True).strip()
        except Exception:
            pass
        return {
            "host": platform.node(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "git_sha": git_sha,
            "base_url": self.base_url,
            "execution_mode": "local_direct",
            "uses_docker": False,
            "serial_model_execution": True,
            "warmup_before_measurement": self._is_ollama_backend(),
        }

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")

    def _write_markdown_comparison(self, path: Path, summaries: list[dict[str, Any]]) -> None:
        lines = [
            "# Local Model Benchmark Comparison",
            "",
            "| Model | Final Score | Tool Selection | Grounded Response | Success Rate | Format Error | Avg Retry | TPS |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for item in sorted(summaries, key=lambda entry: entry["final_score"], reverse=True):
            lines.append(
                "| {model} | {final_score:.4f} | {tool:.4f} | {grounded:.4f} | {success:.4f} | {format_error:.4f} | {retry:.4f} | {tps:.4f} |".format(
                    model=item["model"],
                    final_score=item["final_score"],
                    tool=item["tool_effectiveness"]["correct_tool_selection_rate"],
                    grounded=item["response_quality"]["grounded_response_rate"],
                    success=item["accuracy"]["success_rate"],
                    format_error=item["accuracy"]["format_error_rate"],
                    retry=item["stability"]["avg_retry"],
                    tps=item["speed"]["tokens_per_second"],
                )
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n")

    async def run(self, models: list[str] | None = None, repetitions: int | None = None) -> dict[str, Any]:
        suite = self.load_manifest()
        scenarios = self.load_scenarios(suite)
        selected_models = models or [item.model_id for item in suite.models]
        effective_repetitions = repetitions or suite.defaults.repetitions_per_task
        benchmark_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        environment = self._environment()

        all_attempts: dict[str, list[AttemptResult]] = {model: [] for model in selected_models}
        for model in selected_models:
            if self._is_ollama_backend():
                self._unload_all_loaded_models()
                self._warmup_model(model)

            try:
                for scenario in scenarios:
                    for repetition_index in range(1, effective_repetitions + 1):
                        attempt = await self._run_single_attempt(
                            benchmark_id=benchmark_id,
                            suite=suite,
                            scenario=scenario,
                            model=model,
                            repetition=repetition_index,
                        )
                        all_attempts[model].append(attempt)
                        self._write_json(
                            self.output_dir / "runs" / benchmark_id / model / scenario.id / f"{repetition_index}.json",
                            attempt.model_dump(mode="json"),
                        )
            finally:
                if self._is_ollama_backend():
                    self._unload_model(model)

        average_tps_by_model = {}
        for model, attempts in all_attempts.items():
            total_tps = sum(attempt.metrics.tokens_per_second for attempt in attempts)
            average_tps_by_model[model] = total_tps / len(attempts) if attempts else 0.0
        fastest_tps = max(average_tps_by_model.values(), default=0.0)

        summaries = []
        for model, attempts in all_attempts.items():
            summary = build_summary(
                benchmark_id=benchmark_id,
                suite_id=suite.suite_id,
                suite_version=suite.suite_version,
                model=model,
                attempts=attempts,
                environment=environment,
                normalized_speed=normalize_speed(average_tps_by_model.get(model, 0.0), fastest_tps),
            )
            summary_payload = summary.model_dump(mode="json")
            summaries.append(summary_payload)
            self._write_json(self.output_dir / "summaries" / benchmark_id / f"{model}.json", summary_payload)

        manifest_payload = {
            "benchmark_id": benchmark_id,
            "suite_id": suite.suite_id,
            "suite_version": suite.suite_version,
            "description": suite.description,
            "models": selected_models,
            "repetitions_per_task": effective_repetitions,
            "environment": environment,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write_json(self.output_dir / "manifests" / f"{benchmark_id}.json", manifest_payload)
        self._write_markdown_comparison(
            self.output_dir / "comparisons" / f"{benchmark_id}.md",
            summaries,
        )
        return {"benchmark_id": benchmark_id, "summaries": summaries, "manifest": manifest_payload}


def default_suite_dir() -> Path:
    return Path(__file__).parent / "scenarios" / "suite_v1"


def default_output_dir() -> Path:
    return Path(os.getenv("BENCHMARK_OUTPUT_DIR", "benchmark_results"))
