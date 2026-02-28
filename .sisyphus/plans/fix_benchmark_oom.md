# Work Plan: Benchmark Script OOM Prevention

## Objective
The user correctly identified that the `benchmark_llm.py` script fails to unload models between tests, which will cause the Mac Mini M4 32GB to hit an Out-Of-Memory (OOM) or severe Swap state when loading the 17GB `qwen3.5:35b-a3b` alongside the existing `glm-4.7-flash` footprint.

## Scope
- Modify `scripts/benchmark_llm.py` to add an explicit `unload_model` function that calls the Ollama API with `"keep_alive": 0`.
- Invoke this function at the end of each model's test loop.

## Implementation Steps

### Task 1: Add `unload_model` Function [x]

1. In `scripts/benchmark_llm.py`, define:
```python
def unload_model(client: httpx.Client, model_name: str):
    """Force Ollama to unload the model from memory."""
    print(f"\n  ⏏ Unloading model '{model_name}' from VRAM...", end="", flush=True)
    try:
        resp = client.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "prompt": "", "keep_alive": 0}
        )
        if resp.status_code == 200:
            print(" Done.")
        else:
            print(f" Warning: status {resp.status_code}")
        time.sleep(3) # allow OS to GC
    except Exception as e:
        print(f" Error: {e}")
```

### Task 2: Invoke Unloader [x]

1. Call `unload_model(client, model)` at the end of the `for model in MODELS:` loop (after the `for test in TEST_CASES:` loop concludes).

## Verification
- Run the script manually to ensure it doesn't crash on syntax.
