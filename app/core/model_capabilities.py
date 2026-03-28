from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCapability:
    model_pattern: str
    context_window: int
    max_output_tokens: int | None = None
    tokenizer: str | None = None
    source_url: str | None = None
    note: str | None = None


MODEL_CAPABILITY_CATALOG: tuple[ModelCapability, ...] = (
    # Zhipu GLM
    ModelCapability(
        model_pattern="glm-5-turbo",
        context_window=200_000,
        max_output_tokens=128_000,
        tokenizer="cl100k_base",
        source_url="https://docs.bigmodel.cn/cn/guide/models/text/glm-5-turbo",
    ),
    ModelCapability(
        model_pattern="glm-5",
        context_window=200_000,
        max_output_tokens=128_000,
        tokenizer="cl100k_base",
        source_url="https://docs.bigmodel.cn/cn/guide/models/text/glm-5",
    ),
    ModelCapability(
        model_pattern="glm-4.7-flash",
        context_window=200_000,
        max_output_tokens=128_000,
        tokenizer="cl100k_base",
        source_url="https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash",
    ),
    ModelCapability(
        model_pattern="glm-4.7",
        context_window=200_000,
        max_output_tokens=128_000,
        tokenizer="cl100k_base",
        source_url="https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7",
    ),
    ModelCapability(
        model_pattern="glm-4.6",
        context_window=200_000,
        max_output_tokens=128_000,
        tokenizer="cl100k_base",
        source_url="https://docs.bigmodel.cn/cn/guide/models/text/glm-4.6",
    ),
    ModelCapability(
        model_pattern="glm-4.5",
        context_window=128_000,
        max_output_tokens=96_000,
        tokenizer="cl100k_base",
        source_url="https://docs.bigmodel.cn/cn/guide/models/text/glm-4.5",
    ),
    # DeepSeek
    ModelCapability(
        model_pattern="deepseek-chat",
        context_window=128_000,
        max_output_tokens=8_000,
        source_url="https://api-docs.deepseek.com/quick_start/pricing/",
        note="Official docs list default 4K and maximum 8K output.",
    ),
    ModelCapability(
        model_pattern="deepseek-reasoner",
        context_window=128_000,
        max_output_tokens=64_000,
        source_url="https://api-docs.deepseek.com/quick_start/pricing/",
        note="Official docs list default 32K and maximum 64K output.",
    ),
    # Anthropic
    ModelCapability(
        model_pattern="claude-opus-4-1",
        context_window=200_000,
        max_output_tokens=32_000,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    ),
    ModelCapability(
        model_pattern="claude-opus-4",
        context_window=200_000,
        max_output_tokens=32_000,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    ),
    ModelCapability(
        model_pattern="claude-sonnet-4",
        context_window=200_000,
        max_output_tokens=64_000,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
        note="Docs note 1M context beta is available separately.",
    ),
    ModelCapability(
        model_pattern="claude-3-7-sonnet",
        context_window=200_000,
        max_output_tokens=64_000,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
        note="Docs note 128K output is possible with a beta header.",
    ),
    ModelCapability(
        model_pattern="claude-3-5-sonnet",
        context_window=200_000,
        max_output_tokens=8_192,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    ),
    ModelCapability(
        model_pattern="claude-3-5-haiku",
        context_window=200_000,
        max_output_tokens=8_192,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    ),
    ModelCapability(
        model_pattern="claude-3-haiku",
        context_window=200_000,
        max_output_tokens=4_096,
        source_url="https://docs.anthropic.com/en/docs/about-claude/models",
    ),
    # Google Gemini
    ModelCapability(
        model_pattern="gemini-2.5-pro",
        context_window=1_048_576,
        max_output_tokens=65_536,
        source_url="https://ai.google.dev/gemini-api/docs/models",
    ),
    ModelCapability(
        model_pattern="gemini-2.5-flash",
        context_window=1_048_576,
        max_output_tokens=65_536,
        source_url="https://ai.google.dev/gemini-api/docs/models",
    ),
    ModelCapability(
        model_pattern="gemini-2.5-flash-lite",
        context_window=1_048_576,
        max_output_tokens=65_536,
        source_url="https://ai.google.dev/gemini-api/docs/models",
    ),
    # Qwen / DashScope
    ModelCapability(
        model_pattern="qwen-plus",
        context_window=995_904,
        max_output_tokens=32_768,
        source_url="https://help.aliyun.com/zh/model-studio/models",
        note="Stable alias currently tracks qwen-plus-2025-12-01 in the cited docs.",
    ),
    ModelCapability(
        model_pattern="qwen3.5-plus",
        context_window=1_000_000,
        max_output_tokens=65_536,
        source_url="https://help.aliyun.com/zh/model-studio/models",
    ),
    ModelCapability(
        model_pattern="qwen-max",
        context_window=32_768,
        max_output_tokens=8_192,
        source_url="https://help.aliyun.com/zh/model-studio/getting-started/models",
    ),
)


def lookup_model_capability(model_name: str | None) -> ModelCapability | None:
    normalized = (model_name or "").strip().lower()
    if not normalized:
        return None

    exact_match = None
    prefix_match = None
    for capability in MODEL_CAPABILITY_CATALOG:
        pattern = capability.model_pattern.lower()
        if normalized == pattern:
            exact_match = capability
            break
        if normalized.startswith(pattern) and prefix_match is None:
            prefix_match = capability

    return exact_match or prefix_match
