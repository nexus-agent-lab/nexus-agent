# Model Capability Catalog

Last verified: 2026-03-28

This repository now ships a small built-in model capability catalog for API models that are commonly used through OpenAI-compatible endpoints but are not reliably covered by `tiktoken` model-name mappings.

Priority order at runtime:

1. Explicit config values such as `LLM_CONTEXT_WINDOW`, `LLM_OUTPUT_WINDOW`, and `LLM_TOKENIZER`
2. Built-in catalog match by model name or prefix
3. Repository defaults

Current official source set:

| Provider | Example models | Source |
| --- | --- | --- |
| Zhipu | `glm-5`, `glm-5-turbo`, `glm-4.7`, `glm-4.7-flash`, `glm-4.6`, `glm-4.5` | [docs.bigmodel.cn](https://docs.bigmodel.cn/cn/guide/start/model-overview) |
| DeepSeek | `deepseek-chat`, `deepseek-reasoner` | [api-docs.deepseek.com](https://api-docs.deepseek.com/quick_start/pricing/) |
| Anthropic | `claude-opus-4.1`, `claude-sonnet-4`, `claude-3-7-sonnet`, `claude-3-5-sonnet`, `claude-3-5-haiku` | [docs.anthropic.com](https://docs.anthropic.com/en/docs/about-claude/models) |
| Google Gemini | `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` | [ai.google.dev](https://ai.google.dev/gemini-api/docs/models) |
| Qwen / DashScope | `qwen-plus`, `qwen3.5-plus`, `qwen-max` | [help.aliyun.com](https://help.aliyun.com/zh/model-studio/models) |

Notes:

- The built-in catalog is intended as a runtime default layer, not a permanent source of truth.
- Vendor aliases can move. Stable aliases such as `qwen-plus` may point to newer snapshots over time, so explicit overrides should always win.
- Tokenizer choice remains approximate for many non-OpenAI families. The catalog currently uses tokenizer hints only where we have already standardized behavior in the app.
