import httpx
import json
import time

# --- CONFIGURATION ---
OLLAMA_URL = "http://localhost:11434"

MODELS_TO_TEST = ["glm4.7-flash-32k", "qwen3.5:35b-a3b"]#, "qwen3.5:27b"]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "turn_off_light",
            "description": "Turn off the light in a specific room.",
            "parameters": {
                "type": "object",
                "properties": {"room": {"type": "string", "description": "The room where the light is located."}},
                "required": ["room"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_temperature",
            "description": "Get the current temperature of a room.",
            "parameters": {
                "type": "object",
                "properties": {"room": {"type": "string", "description": "The room to check the temperature."}},
                "required": ["room"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time in a given timezone.",
            "parameters": {
                "type": "object",
                "properties": {"timezone": {"type": "string", "description": "The timezone to check (e.g. UTC, PST)."}},
                "required": ["timezone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_to_log",
            "description": "Save a message to the system log.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "The message to save."}},
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python_sandbox",
            "description": "Execute python code in a secure sandbox.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "The python code to execute."}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather forecast for a location.",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "The location for the weather forecast."}},
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_entities",
            "description": "List all active entities in the home automation system.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a local file.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "The absolute or relative file path."}},
                "required": ["path"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are Nexus Agent, an advanced AI operating system centered around an LLM "CPU" and LangGraph orchestration.
Your primary directive is to Listen, Think, Act, and Reflexion in a continuous loop.
You manage various smart home devices, APIs, file systems, and external services.

<rules>
1. Only use tools that are explicitly provided to you in the environment. Do not assume you have tools not listed.
2. Do not hallucinate tools or capabilities. If a user asks for something you cannot do (like booking a flight, transferring money, etc.), politely decline and explain that you lack the capability.
3. Always prioritize safety and security. Do not execute destructive commands unless explicitly authorized by an admin.
4. For smart home operations, ensure you always verify the room or location before invoking actions.
5. Maintain a professional, concise tone. You do not need to be overly verbose. Just state what you are doing.
6. When using a tool, ensure all required parameters are provided accurately.
7. If multiple tools are needed, use them logically. For conditional requests (e.g., "if X, do Y"), check X first, analyze the response, and then conditionally do Y.
8. If asked for information you don't know, use tools to find it. If you can't find it, admit you don't know.
9. Do not repeat user queries back to them. Get straight to the point.
10. All operations must strictly follow the Nexus Agent Protocol.
</rules>

<context>
Current user: administrator
Environment: Production Smart Home V2
Timezone: UTC
Platform: Nexus Core OS v2.1.4
</context>

<operating_procedures>
- When asked to turn on/off devices, always specify the room if known. If ambiguity exists, assume a generic house context or ask for clarification, but if a room is mentioned, use it.
- When asked for weather, use the get_weather tool.
- When asked to read a file, ensure the path is accurate.
- When asked to run code, use the python_sandbox tool carefully to avoid infinite loops.
- NEVER perform financial transactions or book flights, as you do not have tools for this. If asked, deny the request immediately without calling any tools.
</operating_procedures>

Your goal is to be helpful and safe, adhering strictly to the capabilities exposed via the provided tools.
"""

# Extend SYSTEM_PROMPT slightly to ensure it simulates a realistic size (~500+ tokens)
SYSTEM_PROMPT += " " + " ".join(["Ensure protocol adherence at all times." for _ in range(50)])


def unload_model(client: httpx.Client, model: str):
    print(f"    [System] Unloading model {model} to prevent OOM...")
    try:
        # keep_alive=0 unloads the model from Ollama immediately
        client.post(f"{OLLAMA_URL}/api/generate", json={"model": model, "keep_alive": 0}, timeout=10.0)
    except Exception as e:
        print(f"    [System] Failed to unload model: {e}")


def warmup_model(client: httpx.Client, model: str):
    print(f"    [System] Warming up {model}...")
    try:
        # A simple generation request to load the model into memory
        response = client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": "System check.", "stream": False},
            timeout=180.0,
        )
        if response.status_code != 200:
            print(f"    [System] Warmup returned status {response.status_code}")
    except Exception as e:
        print(f"    [System] Warmup failed: {e}")


def run_test_case(client: httpx.Client, model: str, case_name: str, prompt: str, validator) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "tools": TOOLS,
        "stream": True,
    }

    t0 = time.time()
    ttft = None
    tps = 0.0
    tool_calls = []
    content = ""

    try:
        with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload, timeout=120.0) as response:
            if response.status_code != 200:
                print(f"      [Error] API returned {response.status_code}: {response.read()}")
                return {"ttft": 0.0, "tps": 0.0, "pass": False, "error": f"HTTP {response.status_code}"}

            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg = chunk.get("message", {})

                # Capture TTFT when we get the first meaningful chunk
                # Ollama often sends an empty initial chunk; we wait for content or tool_calls
                if ttft is None:
                    if msg.get("content") or msg.get("tool_calls"):
                        ttft = time.time() - t0

                # Accumulate content and tools
                if msg.get("tool_calls"):
                    tool_calls.extend(msg["tool_calls"])

                if msg.get("content"):
                    content += msg["content"]

                if chunk.get("done"):
                    if ttft is None:
                        ttft = time.time() - t0

                    eval_count = chunk.get("eval_count", 0)
                    eval_duration = chunk.get("eval_duration", 0)

                    if eval_duration > 0:
                        tps = eval_count / (eval_duration / 1e9)  # eval_duration is in nanoseconds

    except Exception as e:
        print(f"      [Error] Exception during stream: {e}")
        return {"ttft": 0.0, "tps": 0.0, "pass": False, "error": str(e)}

    # Convert tool_calls list to string for easy robust matching (even if chunked incorrectly)
    tc_str = json.dumps(tool_calls).lower()
    content_str = content.lower()

    # Run the validation logic
    is_pass = validator(tc_str, content_str)

    return {"ttft": ttft or 0.0, "tps": tps, "pass": is_pass, "error": None}


def main():
    print("==================================================")
    print(" Nexus Agent Benchmark V2 (Realistic Load)")
    print("==================================================")

    # Define test cases and their validators
    # Validator receives stringified tool_calls and content
    test_cases = [
        {
            "name": "Case 1: Single Tool",
            "prompt": "Turn off the bedroom light.",
            "validator": lambda tc, content: "turn_off_light" in tc and "bedroom" in tc,
        },
        {
            "name": "Case 2: Multi Tool",
            "prompt": "Check the temperature in the living room, and if it's hot, turn on the AC.",
            "validator": lambda tc, content: "check_temperature" in tc,
        },
        {
            "name": "Case 3: Anti-Hallucination",
            "prompt": "Book a flight to Paris.",
            "validator": lambda tc, content: tc == "[]",  # Should NOT call any tools
        },
    ]

    results = []

    # Using standard httpx Client for pooling
    with httpx.Client() as client:
        for model in MODELS_TO_TEST:
            print(f"\nEvaluating Model: {model}")

            # 1. Warm-up
            warmup_model(client, model)

            model_metrics = {"model": model, "cases": []}

            # 2. Run Test Cases
            for case in test_cases:
                print(f"  -> Running {case['name']}...")
                res = run_test_case(client, model, case["name"], case["prompt"], case["validator"])

                status = "✅ PASS" if res["pass"] else "❌ FAIL"
                print(f"      Result: {status} | TTFT: {res['ttft']:.2f}s | TPS: {res['tps']:.1f}")

                model_metrics["cases"].append(
                    {"name": case["name"], "ttft": res["ttft"], "tps": res["tps"], "pass": res["pass"]}
                )

            # 3. Prevent OOM by unloading model immediately
            unload_model(client, model)

            results.append(model_metrics)

    # 4. Print clean Markdown Table
    print("\n\n### Benchmark Results")
    print("| Model | Case 1 (Single) | Case 2 (Multi) | Case 3 (Anti-Halluc) | Avg TTFT | Avg TPS |")
    print("|-------|-----------------|----------------|----------------------|----------|---------|")

    for r in results:
        model_name = r["model"]
        c1 = "✅" if r["cases"][0]["pass"] else "❌"
        c2 = "✅" if r["cases"][1]["pass"] else "❌"
        c3 = "✅" if r["cases"][2]["pass"] else "❌"

        # Calculate averages safely
        ttfts = [c["ttft"] for c in r["cases"] if c["ttft"] > 0]
        tpss = [c["tps"] for c in r["cases"] if c["tps"] > 0]

        avg_ttft = sum(ttfts) / len(ttfts) if ttfts else 0.0
        avg_tps = sum(tpss) / len(tpss) if tpss else 0.0

        print(f"| `{model_name}` | {c1} | {c2} | {c3} | {avg_ttft:.2f}s | {avg_tps:.1f} |")


if __name__ == "__main__":
    main()
