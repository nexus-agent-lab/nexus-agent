#!/usr/bin/env python3
import json
import sys
import time

import httpx

MODELS = ["glm4.7-flash-32k", "qwen3.5:35b-a3b"]
OLLAMA_URL = "http://localhost:11434/api/chat"


def generate_heavy_system_prompt() -> str:
    tools = []
    # Generate ~100 fake tools to bloat the context to simulate real Nexus Agent
    for i in range(120):
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": f"system_util_{i}_xyz",
                    "description": f"Internal system utility function {i} for data processing and state management.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resource_id": {"type": "string", "description": "UUID of the resource"},
                            "force": {"type": "boolean", "description": "Force the operation"},
                        },
                        "required": ["resource_id"],
                    },
                },
            }
        )

    # Add relevant tools for the test cases
    tools.extend(
        [
            {
                "type": "function",
                "function": {
                    "name": "turn_off_light",
                    "description": "Turn off a smart light.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "room": {"type": "string", "description": "The room where the light is located"}
                        },
                        "required": ["room"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_temperature",
                    "description": "Check the current temperature of a room or location.",
                    "parameters": {
                        "type": "object",
                        "properties": {"location": {"type": "string", "description": "The location to check"}},
                        "required": ["location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "save_to_log",
                    "description": "Save information to a system log.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "The message to log"},
                            "level": {"type": "string", "description": "Log level (info, warn, error)"},
                        },
                        "required": ["message"],
                    },
                },
            },
        ]
    )

    schema_str = json.dumps(tools, indent=2)
    prompt = f"""You are the Nexus Agent, an advanced AI operating system.
You have access to the following tool schema:
{schema_str}

If the user wants to perform an action, output a valid JSON list of tool calls.
Format:
[
  {{"name": "tool_name", "arguments": {{"key": "value"}}}}
]

If you need to call multiple tools, include them all in the list.
If the user asks for something you cannot do with the provided tools (like booking a flight), output an empty list [] and explain why.
Respond ONLY with the JSON list if tools are needed, or JSON list + explanation.
"""
    return prompt


TEST_CASES = [
    {"name": "Single Tool", "prompt": "Turn off the living room light"},
    {"name": "Multi Tool", "prompt": "Check the temperature in the bedroom and save it to the log"},
    {"name": "Anti-Hallucination", "prompt": "Book a flight to Paris for tomorrow"},
]


def check_accuracy(test_name: str, response: str) -> str:
    response_lower = response.lower()
    if test_name == "Single Tool":
        if "turn_off_light" in response_lower and "living room" in response_lower:
            return "Pass"
        return "Fail"
    elif test_name == "Multi Tool":
        if "check_temperature" in response_lower and "save_to_log" in response_lower:
            return "Pass"
        return "Fail"
    elif test_name == "Anti-Hallucination":
        # It should decline or output empty list without hallucinating a book_flight tool
        if "book_flight" in response_lower or "bookflight" in response_lower:
            return "Fail"
        if (
            "[]" in response_lower
            or "cannot" in response_lower
            or "don't have" in response_lower
            or "unable" in response_lower
        ):
            return "Pass"
        # If it didn't use a fake tool, maybe it just explained
        if "system_util" not in response_lower:
            return "Pass (Explanation)"
        return "Fail"
    return "Unknown"


def unload_model(client: httpx.Client, model_name: str):
    """Force Ollama to unload the model from memory."""
    print(f"\n  ⏏ Unloading model '{model_name}' from VRAM...", end="", flush=True)
    try:
        resp = client.post(
            "http://localhost:11434/api/generate", json={"model": model_name, "prompt": "", "keep_alive": 0}
        )
        if resp.status_code == 200:
            print(" Done.")
        else:
            print(f" Warning: status {resp.status_code}")
        time.sleep(3)  # allow OS to GC
    except Exception as e:
        print(f" Error: {e}")


def run_benchmark():
    system_prompt = generate_heavy_system_prompt()
    print(f"Generated fake Tool Schema system prompt of length: {len(system_prompt)} chars")

    results = {model: [] for model in MODELS}

    with httpx.Client(timeout=180.0) as client:
        for model in MODELS:
            print(f"\n--- Benchmarking Model: {model} ---")

            # Check if model exists locally in Ollama
            try:
                resp = client.post("http://localhost:11434/api/show", json={"name": model})
                if resp.status_code != 200:
                    print(f"Model '{model}' not found in Ollama or error ({resp.status_code}). Skipping.")
                    continue
            except Exception as e:
                print(f"Error connecting to Ollama at {OLLAMA_URL}: {e}")
                print("Make sure Ollama is running.")
                sys.exit(1)

            for test in TEST_CASES:
                print(f"Running test: {test['name']} ...", end="", flush=True)

                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": test["prompt"]},
                    ],
                    "stream": True,
                    "options": {"temperature": 0.1},
                }

                try:
                    start_time = time.time()
                    ttft = None
                    full_response = ""
                    eval_count = 0
                    eval_duration = 0

                    with client.stream("POST", OLLAMA_URL, json=payload) as response:
                        for line in response.iter_lines():
                            if not line:
                                continue
                            data = json.loads(line)

                            if ttft is None and "message" in data and data["message"].get("content"):
                                ttft = time.time() - start_time

                            if "message" in data and "content" in data["message"]:
                                full_response += data["message"]["content"]

                            if data.get("done"):
                                eval_count = data.get("eval_count", 0)
                                eval_duration = data.get("eval_duration", 0)  # in nanoseconds
                                break

                    if eval_duration > 0:
                        tps = eval_count / (eval_duration / 1e9)
                    else:
                        end_time = time.time()
                        time_taken = end_time - (start_time + (ttft or 0))
                        tps = eval_count / time_taken if time_taken > 0 else 0

                    accuracy = check_accuracy(test["name"], full_response)

                    print(f" Done! (TTFT: {ttft or 0.0:.2f}s, TPS: {tps:.1f}, Accuracy: {accuracy})")

                    results[model].append(
                        {
                            "test": test["name"],
                            "ttft": ttft or 0.0,
                            "tps": tps,
                            "accuracy": accuracy,
                            "response": full_response,
                        }
                    )

                except Exception as e:
                    print(f" Error: {e}")
                    results[model].append(
                        {"test": test["name"], "ttft": 0.0, "tps": 0.0, "accuracy": "Error", "response": str(e)}
                    )
            # Unload model to prevent OOM
            unload_model(client, model)

    print("\n\n" + "=" * 85)
    print(f"{'BENCHMARK RESULTS':^85}")
    print("=" * 85)

    # Print Markdown/ASCII Table
    print(f"| {'Model':<20} | {'Test Case':<20} | {'TTFT (s)':<10} | {'TPS':<10} | {'Accuracy':<10} |")
    print(f"| {'-' * 20} | {'-' * 20} | {'-' * 10} | {'-' * 10} | {'-' * 10} |")

    for model, tests in results.items():
        if not tests:
            print(f"| {model:<20} | {'SKIPPED (Not Found)':<20} | {'-':<10} | {'-':<10} | {'-':<10} |")
            continue

        for t in tests:
            ttft_str = f"{t['ttft']:.2f}"
            tps_str = f"{t['tps']:.1f}"
            print(f"| {model:<20} | {t['test']:<20} | {ttft_str:<10} | {tps_str:<10} | {t['accuracy']:<10} |")

    print("=" * 85)


if __name__ == "__main__":
    run_benchmark()
