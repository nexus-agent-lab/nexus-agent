# Nexus Agent: Local LLM Selection & Benchmarking Guide

This guide summarizes the benchmarking results for various open-source models running on **Apple Silicon (Mac Mini M4, 32GB RAM)** and provides a protocol for testing new models in the future.

---

## 📊 Benchmark Results (Feb 2028)

We tested three primary contenders under a "Realistic Agent Load" (8 tools, ~3,000 token context).

| Model | Avg TTFT (Latency) | Avg TPS (Throughput) | Tool Accuracy | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **GLM-4.7-Flash** | **~5.9s** | **25.4 tok/s** | **100%** | 🏆 **Winner**: Best conversational UX. |
| **Qwen3.5-35B-A3B** | ~13.4s | 17.7 tok/s | 100% | 🥈 **Runner Up**: Smart but high latency. |
| **Qwen3.5-27B (Dense)**| ~61.1s | 4.3 tok/s | 100% | ❌ **Fail**: Saturated memory/Swap. |

### Key Findings:
1.  **Memory is the Hard Ceiling**: On a 32GB Mac, 35B models (MoE) or 14B-20B models (Dense) are the limit. Anything larger triggers **SSD Swap**, dropping speed by 90%.
2.  **Prefill vs. Decode**: Even with 3B active parameters (MoE), the initial "Prefill" stage (reading the prompt) on a 35B model still takes ~13 seconds. Small dense models (9B) are 2x faster at starting.
3.  **Software > Hardware**: Our **Semantic Tool Router** is the secret weapon. By narrowing 100+ tools down to 8, we allow "smaller" models like GLM-4.7 to achieve 100% accuracy while keeping responses under 6 seconds.

---

## 🛠️ How to Benchmark New Models

Whenever a new state-of-the-art (SOTA) open-source model is released, follow these steps to see if it's suitable for Nexus OS.

### 1. Download Contenders
Use Ollama to pull the new model (Recommended quantization: **Q4_K_M** or **Q5_K_M**).
```bash
ollama pull <model_name>
```

### 2. Configure for Nexus OS
Create a Modelfile to ensure the model isn't "thinking" too much (suppress CoT) and has the correct context window.
```dockerfile
FROM <model_name>
PARAMETER num_ctx 8192
PARAMETER temperature 0.1
SYSTEM "You are a precise tool-calling assistant. Output ONLY JSON."
```

### 3. Run the Automated Benchmark
We provide a standalone profiling script that simulates the real Nexus Agent environment.
```bash
# Run the realistic load test (V2)
python3 scripts/benchmark_v2.py
```

### 4. Evaluate the "5-Second Rule"
*   **TTFT < 5s**: Perfect. The system feels like an OS.
*   **TTFT 5-10s**: Acceptable, but needs a "thinking..." indicator in the UI.
*   **TTFT > 15s**: Too slow for an interactive agent.

---

## 💡 Future Recommendations for M4 32GB
- **MoE is the Future**: Models with high total parameters but low active parameters (like Qwen MoE) are ideal for Mac's "High RAM, Mid Bandwidth" architecture.
- **Stay below 20GB**: Always ensure `Model Weights + (Context Window * 0.5MB)` < 24GB to avoid Swap.
