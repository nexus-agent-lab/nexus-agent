# Local Model Benchmark Usage

This is the operational guide for the new local model benchmark subfunction.

## What It Measures

The benchmark currently prioritizes:

1. tool selection correctness
2. grounded final response quality
3. error rate and retry burden

Speed is included, but it is secondary.

## Local Runtime Rules

This benchmark is intended to run directly on the local machine.

Rules:

1. do not use Docker for model execution
2. run one model at a time
3. warm the model before the measured benchmark starts
4. unload the previous model before loading the next one

For Ollama backends, the current runner now enforces this automatically:

- it tries to unload already loaded models before switching
- it performs one warmup request for the target model
- it runs the benchmark after warmup
- it unloads the tested model after that model's batch is finished

This makes cross-model comparison fairer on local Macs where RAM pressure and model residency can otherwise skew results.

## Current Suite

The first runnable suite lives in:

- [app/benchmarks/scenarios/suite_v1/manifest.json](/Users/michael/work/nexus-agent/app/benchmarks/scenarios/suite_v1/manifest.json)

It contains five fixed tasks:

1. basic tool call
2. multi-tool routing
3. multi-step reasoning
4. error recovery
5. long context

## How To Run

Example:

```bash
python3 scripts/run_local_model_benchmark.py \
  --models glm4.7-flash mistral-small:24b devstral:24b \
  --base-url http://localhost:11434/v1 \
  --api-key ollama \
  --repetitions 5
```

If `LLM_BASE_URL` and `LLM_API_KEY` are already set, you can omit them.

This command runs locally against Ollama and does not require Docker.

## Output

Results are written to:

```text
benchmark_results/
  manifests/
  runs/
  summaries/
  comparisons/
```

Key files:

- raw per-attempt JSON under `benchmark_results/runs/...`
- per-model summary JSON under `benchmark_results/summaries/...`
- Markdown comparison table under `benchmark_results/comparisons/...`
- run manifest includes execution metadata such as local-direct mode, non-Docker execution, serial model execution, and warmup behavior

## How To Compare Models

The comparison Markdown file ranks models by:

- final score
- tool selection rate
- grounded response rate
- success rate
- format error rate
- avg retry
- tokens per second

This makes it easy to compare multiple local models after one batch run.

## Notes

This is the minimum useful version.

The current implementation uses deterministic fixture tools so that:

- tasks stay stable across runs
- external systems do not add noise
- model comparisons remain fair

The next step can deepen LangGraph-path reuse if we want the benchmark to mirror the production graph even more closely.
