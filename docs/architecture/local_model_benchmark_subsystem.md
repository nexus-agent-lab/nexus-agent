# Local Model Benchmark Subsystem

> Status: Direction Draft
> Date: 2026-03-25
> Intent: Add a repeatable LangGraph-native benchmark subsystem for evaluating which local model is the best fit for Nexus Agent on Apple Silicon.

## 1. Objective

This document defines a dedicated **local model benchmark subsystem** for Nexus Agent.

The goal is not to measure general chat intelligence.

The goal is to answer one operational question:

**Which local model delivers the best combined stability, correctness, and efficiency inside the real Nexus LangGraph agent loop?**

More specifically, the benchmark should prioritize three practical questions above all else:

1. **Toolset query effectiveness**
   - can the model pick the right tool from the available toolset
   - can it avoid wrong or unnecessary tool calls
2. **Response quality**
   - is the final answer grounded, useful, complete, and aligned with the tool result
3. **Error rate**
   - how often does the model produce malformed calls, invalid arguments, retries, or hallucinated outputs

This subsystem should become a durable project capability so that:

- a newly released local model can be added by configuration
- the same benchmark suite can be rerun without prompt drift
- every run is archived for later comparison
- benchmark conclusions remain traceable to raw executions

The first intended hardware target is:

- Mac mini M4
- 32GB RAM
- Ollama-based local inference

---

## 2. Why This Should Be A Subsystem

The repository already has pieces of the required foundation:

- LangGraph orchestration in [app/core/agent.py](/Users/michael/work/nexus-agent/app/core/agent.py)
- model bootstrapping in [app/core/llm_utils.py](/Users/michael/work/nexus-agent/app/core/llm_utils.py)
- retry and recovery semantics in `WorkerDispatcher`
- LLM trace storage in [app/models/llm_trace.py](/Users/michael/work/nexus-agent/app/models/llm_trace.py)
- an older standalone benchmark in [scripts/benchmark_v2.py](/Users/michael/work/nexus-agent/scripts/benchmark_v2.py)
- local model guidance in [docs/local_model_guide.md](/Users/michael/work/nexus-agent/docs/local_model_guide.md)

What is missing is a **single, official evaluation path** that is:

- agent-first rather than chat-first
- configuration-driven rather than hardcoded
- reproducible rather than ad hoc
- archival rather than ephemeral
- comparable across dates, models, and code revisions

So this should not remain a loose script under `scripts/`.

It should become a small benchmark subsystem with:

1. benchmark scenario definitions
2. runner orchestration
3. metrics extraction
4. score calculation
5. result archival
6. historical comparison views

---

## 3. Non-Goals

This subsystem should not try to become:

- a generic public leaderboard
- a full academic eval framework
- a replacement for production runtime tracing
- a benchmark that mixes changing prompts, changing tools, and changing schemas in one score

It is specifically for **Nexus-fit evaluation**.

That means the benchmark should prefer:

- real tool use
- real LangGraph control flow
- real retry / recovery paths
- real Nexus-style context length
- stable and versioned fixtures

---

## 4. Core Product Requirement

The benchmark subsystem should answer:

1. Can this model call Nexus tools correctly?
2. Can it survive the Nexus retry / recovery loop without collapsing?
3. Can it keep multi-turn task intent stable over long context?
4. Can it do this fast enough on M4 32GB to feel usable?
5. Is it better than the models we already tested?

The benchmark output should therefore emphasize:

- tool-selection correctness first
- response quality second
- error rate / stability third
- retry burden fourth
- speed fifth

This matches the product reality of the current agent.

---

## 5. Evaluation Principle

The benchmark must be **agent-first**.

A model should not win because it sounds smart in a single turn.

A model should win because it can repeatedly complete the same Nexus workflow with:

- correct tool choice
- correct tool arguments
- high-quality grounded final response
- correct recovery behavior
- low hallucination
- acceptable speed

That means benchmark scenarios should be executed through the **same LangGraph execution path** used by the project, or as close to it as possible.

The desired order of fidelity is:

1. full LangGraph benchmark path with benchmark-only fixture tools
2. shared Nexus tool-calling path with LangGraph-compatible state and tracing
3. raw Ollama chat benchmark only as an early smoke test, not the final benchmark

The current `scripts/benchmark_v2.py` should be treated as a legacy seed, not the target end state.

---

## 6. Recommended Architecture

### 6.1 Subsystem Boundaries

Add a new benchmark subsystem with four layers:

1. **Scenario Layer**
   - versioned benchmark tasks
   - stable prompts
   - stable expected outcomes
   - stable fixture tools and fixture data

2. **Runner Layer**
   - iterates models
   - iterates tasks
   - repeats runs
   - collects raw run artifacts

3. **Metrics Layer**
   - computes success, format error, retry count, hallucination, latency, TPS
   - produces normalized scores

4. **Archive Layer**
   - writes benchmark manifests
   - stores raw execution logs
   - stores summarized JSON results
   - supports later comparison

### 6.2 Recommended Repository Layout

Recommended target layout:

```text
app/
  benchmarks/
    __init__.py
    models.py
    runner.py
    scoring.py
    evaluators.py
    fixtures/
      tools.py
      datasets/
    scenarios/
      suite_v1/
        manifest.yaml
        task_01_tool_call.yaml
        task_02_multi_tool.yaml
        task_03_multi_step.yaml
        task_04_error_recovery.yaml
        task_05_long_context.yaml

scripts/
  run_local_model_benchmark.py

benchmark_results/
  manifests/
  runs/
  summaries/
  comparisons/
```

Rationale:

- `app/benchmarks/` keeps benchmark logic versioned with application code
- `scripts/run_local_model_benchmark.py` provides a thin execution entrypoint
- `benchmark_results/` keeps result archives separate from app runtime data

This is better than writing everything into `scripts/` because benchmark logic will evolve with the agent architecture.

---

## 7. Configuration Model

The benchmark subsystem should be configuration-driven.

A new model should be benchmarkable by editing configuration, not rewriting code.

### 7.1 Benchmark Manifest

The benchmark suite should have a versioned manifest, for example:

```yaml
suite_id: nexus_local_models_v1
suite_version: 1
description: LangGraph-local-model benchmark for M4 32GB
defaults:
  temperature: 0.2
  top_p: 0.9
  max_tokens: 2048
  repetitions_per_task: 8
  warmup_runs: 1
  timeout_seconds: 120
tasks:
  - task_01_tool_call
  - task_02_multi_tool
  - task_03_multi_step
  - task_04_error_recovery
  - task_05_long_context
models:
  - name: glm4.7-flash
    provider: ollama
    model_id: glm4.7-flash
  - name: mistral-small:24b
    provider: ollama
    model_id: mistral-small:24b
  - name: devstral:24b
    provider: ollama
    model_id: devstral:24b
  - name: qwen3.5:27b
    provider: ollama
    model_id: qwen3.5:27b
```

### 7.2 Scenario Definition

Each task file should define:

- task id
- task type
- user input
- optional conversation history
- available fixture tools
- expected tool sequence
- expected success conditions
- error injection behavior
- hallucination rules

The scenario file should be the source of truth for reproducibility.

### 7.3 Environment Fingerprint

Each benchmark run should also record:

- hostname
- chip / CPU class
- RAM
- Ollama version
- model digest if available
- git commit SHA
- benchmark suite version
- date and timezone

Without this, cross-run comparison will become noisy and misleading.

---

## 8. Recommended Benchmark Tasks

The first official suite should implement the five tasks you defined, but translate them into Nexus-native fixtures.

Across all five tasks, the benchmark should score three top-level dimensions:

1. toolset query effectiveness
2. response quality
3. error rate

Other metrics such as speed and retry count remain important, but they are support metrics rather than the primary decision axis.

### 8.1 Task 1: Basic Tool Call

Purpose:

- verify simple tool selection and argument formatting

Checks:

- correct tool chosen
- JSON / schema valid
- success on first attempt

Recommended fixture tools:

- `fixture_get_weather`
- `fixture_calculator`

### 8.2 Task 2: Multi-Tool Routing

Purpose:

- verify correct selection from multiple available tools

Checks:

- correct tool chosen
- no irrelevant tool call
- limited retries

Recommended fixture tools:

- `fixture_read_file`
- `fixture_calculator`
- `fixture_search`

### 8.3 Task 3: Multi-Step Reasoning + Tool

Purpose:

- verify reasoning, tool use, and final synthesis remain connected

Checks:

- no missing intermediate step
- no fabricated result
- answer grounded in tool output

Recommended fixture:

- one scenario where the user asks a derived question that requires reading data, computing a conclusion, and summarizing it

### 8.4 Task 4: Error Recovery

Purpose:

- verify the model survives a failing tool path

Checks:

- recognizes the tool error
- retries when appropriate
- changes strategy when the first attempt is invalid

Recommended fixture:

- first tool call fails deterministically
- second path succeeds if the model corrects arguments or chooses a safer tool

This is the most important task because it measures agent stability, not just first-pass accuracy.

### 8.5 Task 5: Long Context

Purpose:

- verify the model remains aligned after 10+ turns

Checks:

- maintains task target
- preserves prior facts
- avoids repeated or duplicate tool calls
- does not drift to unrelated goals

Recommended fixture:

- a synthetic conversation history with stable facts, one earlier failed attempt, and one pending user objective

---

## 9. Fixture Tool Strategy

The benchmark should not use random live tools for scoring.

That would make results unstable across runs.

Instead, the benchmark should use **benchmark fixture tools** that mimic real Nexus tool semantics while returning deterministic outputs.

### 9.1 Why Fixture Tools

Fixture tools allow:

- identical outputs across models
- controlled failure cases
- stable hallucination detection
- safe offline repeatability

### 9.2 Design Rule

Fixture tools should look like real Nexus tools:

- same function-calling style
- real schemas
- realistic names and descriptions
- realistic payload shapes

But they must return fixed fixture data from local datasets.

### 9.3 Error Injection

Task 4 should support explicit error-injection modes such as:

- transient failure once, then success
- invalid parameter rejection
- resource-not-found requiring discovery fallback

This lets us evaluate whether the model adapts instead of blindly repeating the same call.

---

## 10. Execution Path Recommendation

### 10.1 Preferred Path

The official benchmark should run through a dedicated **benchmark graph path** that reuses:

- LangGraph state handling
- tool binding
- retry logic
- trace logging
- result classification

But swaps in fixture tools instead of production MCP tools.

This preserves agent realism without needing Home Assistant, Playwright, or external services to be online.

### 10.2 Why Not Raw Ollama Chat Only

A raw Ollama function-calling test is useful for smoke checks, but it misses:

- LangGraph routing effects
- retry policy behavior
- reviewer / verification transitions
- state accumulation across turns
- Nexus-specific failure semantics

So raw-model testing should remain optional and secondary.

### 10.3 Benchmark Execution Modes

Support two modes:

1. `smoke`
   - raw or near-raw tool calling
   - fast candidate filtering

2. `full`
   - LangGraph-native benchmark path
   - official score for project decision-making

Only `full` mode should decide which model is recommended for Nexus.

---

## 11. Metrics Definition

The benchmark subsystem should compute the following metrics for each model.

### 11.1 Speed

Store:

- `tokens_per_second`
- `time_to_first_token` when available
- `total_completion_time`
- `avg_latency`

### 11.2 Success Rate

Primary metric:

```text
success_rate = successful_runs / total_runs
```

A run is successful only if:

- the correct tools are called
- parameters validate
- the expected result is reached
- the final response is grounded in the actual tool result
- no human intervention is needed

### 11.3 Format Error Rate

```text
format_error_rate = format_errors / total_tool_calls
```

Includes:

- JSON parse failure
- missing required parameter
- schema mismatch
- invalid argument type

### 11.4 Average Retry

```text
avg_retry = total_retries / total_runs
```

This should count retries inside the agent flow, not only external reruns.

### 11.5 Hallucination Rate

```text
hallucination_rate = hallucinated_runs / total_runs
```

Hallucination means any of:

- invented tool
- invented tool output
- final answer contradicts the actual fixture tool result
- tool-free fabricated answer when the task required tool grounding

### 11.6 Stability Detail

Store additional breakdown fields even if they are not all in the final score:

- `first_attempt_success_rate`
- `retry_recovery_success_rate`
- `wrong_tool_rate`
- `duplicate_tool_call_rate`
- `context_drift_rate`

### 11.7 Toolset Query Effectiveness

This should be a first-class benchmark dimension, not only a hidden submetric.

Store:

- `correct_tool_selection_rate`
- `wrong_tool_selection_rate`
- `unnecessary_tool_call_rate`
- `tool_order_correctness_rate`

This dimension answers the most important agent-runtime question:

**when the model sees the available Nexus tools, does it query and use the toolset correctly?**

### 11.8 Response Quality

This should also be a first-class benchmark dimension.

Response quality should be judged against a deterministic rubric:

- grounded in actual tool output
- answers the user request directly
- includes the needed conclusion or synthesis
- does not omit key results
- does not fabricate unsupported details

Store:

- `grounded_response_rate`
- `complete_response_rate`
- `response_deviation_rate`

For phase 1, these can be evaluator-based rubric scores derived from the fixture result and expected answer contract.

These will help explain why two models with similar total scores behave differently.

---

## 12. Score Formula

Use one official score formula and keep it versioned.

The initial formula should reflect the real project priority:

- toolset query effectiveness
- response quality
- low error rate
- stable recovery
- speed as a secondary efficiency signal

Recommended initial formula:

```text
final_score =
  (0.30 × correct_tool_selection_rate)
+ (0.25 × grounded_response_rate)
+ (0.20 × (1 - format_error_rate))
+ (0.15 × (1 - retry_rate))
+ (0.10 × normalized_speed)
```

Notes:

- `retry_rate` should be derived from average retries and normalized into `[0,1]`
- `normalized_speed` must be normalized only against models in the same benchmark batch
- the formula version should be stored with the result archive
- `hallucination_rate` should remain in the raw summary and should be used as a failure annotation even when not separately weighted in this first score version

This is important because score formulas may evolve later.

The archive must always preserve:

- raw metrics
- score formula version
- final score

So historical results can be recomputed if needed.

---

## 13. Result Schema

Each model summary should be emitted in a standard JSON shape:

```json
{
  "suite_id": "nexus_local_models_v1",
  "suite_version": 1,
  "model": "mistral-small:24b",
  "environment": {
    "host": "mac-mini-m4",
    "ram_gb": 32,
    "inference_backend": "ollama"
  },
  "speed": {
    "tokens_per_second": 12.5,
    "avg_latency": 3.2,
    "ttft": 1.9,
    "total_completion_time": 4.7
  },
  "tool_effectiveness": {
    "correct_tool_selection_rate": 0.91,
    "wrong_tool_selection_rate": 0.06,
    "unnecessary_tool_call_rate": 0.04
  },
  "response_quality": {
    "grounded_response_rate": 0.89,
    "complete_response_rate": 0.84,
    "response_deviation_rate": 0.08
  },
  "accuracy": {
    "success_rate": 0.88,
    "format_error_rate": 0.05,
    "hallucination_rate": 0.07
  },
  "stability": {
    "avg_retry": 1.2,
    "first_attempt_success_rate": 0.64,
    "retry_recovery_success_rate": 0.24
  },
  "final_score": 0.82
}
```

This summary JSON should be accompanied by raw per-run records.

---

## 14. Archival Strategy

Historical comparison is a first-class requirement.

So every benchmark invocation should write three artifact levels.

### 14.1 Run Manifest

One manifest per batch run:

- benchmark id
- suite version
- models tested
- repetitions
- config defaults
- git SHA
- hardware fingerprint
- started / completed timestamps

Suggested path:

```text
benchmark_results/manifests/<benchmark_id>.json
```

### 14.2 Raw Run Records

One record per model-task-attempt:

- benchmark id
- model
- task id
- repetition index
- prompt hash
- conversation hash
- tool sequence
- errors
- retries
- timing
- final evaluator verdict

Suggested path:

```text
benchmark_results/runs/<benchmark_id>/<model>/<task>/<attempt>.json
```

### 14.3 Summary Records

One summary per model per benchmark batch:

Suggested path:

```text
benchmark_results/summaries/<benchmark_id>/<model>.json
```

### 14.4 Comparison Records

Generated comparison views:

- same suite, multiple models
- same model, multiple dates
- before/after code changes

Suggested path:

```text
benchmark_results/comparisons/<comparison_id>.json
```

---

## 15. Trace Integration

The benchmark subsystem should reuse existing LLM trace logging where practical, but benchmark data should not depend only on the production `llm_trace` table.

Recommended rule:

- keep normal `LLMTrace` writes available for debugging
- also write benchmark-specific raw JSON artifacts as the canonical benchmark archive

Why:

- benchmark archives need scenario metadata and evaluator verdicts that do not belong in generic runtime traces
- database contents may be rotated or filtered later
- raw files are easier to diff, export, and compare in Git or external tools

If benchmark-specific database tables are added later, that should be a second phase, not a blocker for phase 1.

---

## 16. Model Onboarding Workflow

When a new model appears, the intended workflow should be:

1. add the model entry to the benchmark manifest
2. ensure Ollama model is available locally
3. run benchmark in `smoke` mode
4. run benchmark in `full` mode
5. archive results automatically
6. compare against the current recommended baseline
7. decide whether to promote it into normal local-model guidance

This is the key maintainability win.

No scenario prompt should be edited during this process.

If prompt changes are needed, that means:

- create a new suite version
- preserve the old suite for comparability

---

## 17. Versioning Rules

To keep benchmark results meaningful over time, version these separately:

1. **suite version**
   - task definitions changed
   - prompt wording changed
   - fixture data changed

2. **score formula version**
   - weights changed
   - normalization logic changed

3. **runner version**
   - benchmark execution logic changed

If any of those change materially, the benchmark result should record the new version and avoid pretending the numbers are directly identical.

---

## 18. Recommended Implementation Phases

### Phase 1: Minimum Useful Benchmark

Deliver:

- versioned scenario files
- fixture tools
- batch runner
- JSON summaries
- raw archive output
- score calculation

This phase should be enough to benchmark:

- `glm4.7-flash`
- `mistral-small:24b`
- `devstral:24b`
- `qwen3.5:27b` when available

### Phase 2: LangGraph-Native Integration

Deliver:

- benchmark runner reusing more of the real `app/core/agent.py` path
- benchmark-specific trace enrichment
- long-context scenario support with full state replay

### Phase 3: Admin / Reporting UX

Deliver:

- comparison report generator
- optional admin page or CLI table view
- trend views across benchmark history

Phase 3 is nice to have, not required for the first useful version.

---

## 19. Concrete Recommendation For This Repository

Given the current repository state, the best next implementation path is:

1. keep the existing production agent unchanged
2. create a dedicated `app/benchmarks/` module
3. migrate useful parts of `scripts/benchmark_v2.py` into the new module
4. replace raw hardcoded prompts with versioned scenario YAML
5. use deterministic fixture tools instead of live external tools
6. archive every raw run under `benchmark_results/`
7. update [docs/local_model_guide.md](/Users/michael/work/nexus-agent/docs/local_model_guide.md) only after the new subsystem becomes the official source of benchmark truth

This gives the project a repeatable benchmark feature without coupling it to unstable external dependencies.

---

## 20. Sanity-Check Expectations

The benchmark should support qualitative interpretation such as:

- `GLM4.7 Flash`
  - likely fastest
  - likely more retries

- `Mistral Small 24B`
  - likely strongest format stability
  - likely strongest steady agent behavior

- `Devstral 24B`
  - likely strongest on code-adjacent tool tasks
  - possibly slower

- `Qwen3.5 27B`
  - likely stronger Chinese handling
  - stability still needs measurement under the same suite

These are only sanity-check expectations, not benchmark truth.

The subsystem exists to replace intuition with archived evidence.

---

## 21. Final Decision

This feature should be treated as a **project subfunction**, not a temporary script.

The official benchmark path should be:

- scenario-versioned
- LangGraph-aware
- config-driven
- archive-first
- comparable across time

If implemented this way, Nexus will be able to answer, with evidence:

**Which local model is currently the best operational fit for this project, on this hardware, under this agent architecture?**

In practical terms, the benchmark should primarily tell us:

- which model is best at choosing from the current toolset
- which model gives the best grounded final replies
- which model has the lowest error rate in the real agent loop
