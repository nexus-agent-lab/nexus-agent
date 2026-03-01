"""
Profile the latency of GLM-4-Flash as a Tier-0 "Fast Brain" intent router.
Tests whether local LLM intent extraction is fast enough to justify
a pre-routing step before the full Agent pipeline.

Usage:
    PYTHONPATH=. python scripts/debug/profile_intent_router.py
"""

import json
import os
import sys
import time

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm_utils import get_llm_client

# ─── Config ───────────────────────────────────────────────────────
# Added Extreme Anti-CoT (Anti-Thinking) Directives
ROUTER_SYSTEM_PROMPT = """You are a stateless JSON converter.
Your ONLY job is to extract distinct user actions into a JSON array of strings.
CRITICAL RULES:
1. DO NOT THINK. DO NOT REASON. DO NOT USE <think> TAGS.
2. DO NOT output any markdown formatting like ```json.
3. YOUR FIRST AND ONLY OUTPUT MUST BE A VALID JSON ARRAY.
4. DO NOT EXPLAIN YOUR OUTPUT.

Examples:
["turn_off_lights"]
["check_temperature", "log_to_feishu"]"""

TEST_CASES = [
    {
        "label": "Single intent (Chinese, short)",
        "input": "查一下客厅温度。",
        "expected_count": 1,
    },
    {
        "label": "Multi-intent (mixed language)",
        "input": "Qual è la temperatura? 然后把结果记录到我的 Feishu 日志里",
        "expected_count": 2,
    },
]

# Number of runs per test case for stable median
WARM_UP_RUNS = 1
BENCH_RUNS = 3


def run_profile():
    print("=" * 64)
    print("  Fast Brain Latency Profiler (ANTI-CoT MODE)")
    print(f"  Model: {os.getenv('LLM_MODEL', 'unknown')}")
    print(f"  Base URL: {os.getenv('LLM_BASE_URL', 'unknown')}")
    print("=" * 64)

    # Use the same factory the agent uses
    llm = get_llm_client(temperature=0.0)  # Absolute zero temperature for JSON formatting

    # ─── Warm-up ───────────
    print("\n⏳ Warm-up call (model loading into memory)...")
    t0 = time.perf_counter()
    try:
        llm.invoke(
            [
                SystemMessage(content='Reply with JSON: ["ready"]'),
                HumanMessage(content="ping"),
            ]
        )
        warmup_ms = (time.perf_counter() - t0) * 1000
        print(f"   Warm-up: {warmup_ms:.0f}ms\n")
    except Exception as e:
        print(f"❌ Failed to connect to LLM: {e}")
        return

    # ─── Benchmark each test case ─────────────────────────────────
    results = []

    for case in TEST_CASES:
        print(f"─── {case['label']} ───")
        print(f'    Input: "{case["input"]}"')

        messages = [
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=case["input"]),
        ]

        latencies = []
        last_output = None

        for run_idx in range(WARM_UP_RUNS + BENCH_RUNS):
            t0 = time.perf_counter()
            response = llm.invoke(messages)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            # Skip warm-up runs for stats
            if run_idx >= WARM_UP_RUNS:
                latencies.append(elapsed_ms)
                last_output = response.content

        # ─── Parse & validate output ──────────────────────────────
        parsed = None
        parse_ok = False
        try:
            raw = last_output.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            if "[" in raw and "]" in raw:
                raw = raw[raw.find("[") : raw.rfind("]") + 1]
            parsed = json.loads(raw)
            parse_ok = isinstance(parsed, list) and len(parsed) >= 1
        except Exception as e:
            print(f"    [Debug] Parse error: {e} on raw text: '{last_output}'")

        avg_ms = sum(latencies) / len(latencies)

        quality = "✅" if parse_ok and len(parsed) >= case["expected_count"] else "⚠️"
        count_info = f"{len(parsed)}/{case['expected_count']}" if parsed else "PARSE_FAIL"

        print(f"    Output: {last_output}")
        print(f"    Quality: {quality} (intents: {count_info})")
        print(f"    Latency: avg={avg_ms:.0f}ms")
        print()
        results.append({"avg_ms": avg_ms})

    overall_avg = sum(r["avg_ms"] for r in results) / len(results)
    print("=" * 64)
    print(f"  Average latency across all cases: {overall_avg:.0f}ms")


if __name__ == "__main__":
    run_profile()
