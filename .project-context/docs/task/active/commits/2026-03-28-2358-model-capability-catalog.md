# Checkpoint

## Intent
Add a built-in model capability catalog so the runtime can infer context window, output window, and selected tokenizer hints for common API models that are not reliably covered by `tiktoken` model-name mappings.

## Previous Context
- The app already used `LLM_CONTEXT_WINDOW`, `LLM_OUTPUT_WINDOW`, and `LLM_TOKENIZER`, but only as static defaults or explicit configuration.
- `glm-5-turbo` had already been aliased to `cl100k_base` to reduce degraded tokenizer warnings.
- The user asked for an internet-verified built-in capability database for current API models, especially beyond what `tiktoken` recognizes.

## Changes Made
- Added [app/core/model_capabilities.py](/Users/michael/work/nexus-agent/app/core/model_capabilities.py) with a built-in catalog covering common non-OpenAI model families:
  - Zhipu GLM
  - DeepSeek
  - Anthropic Claude
  - Google Gemini
  - Qwen / DashScope
- Added [docs/architecture/model_capability_catalog.md](/Users/michael/work/nexus-agent/docs/architecture/model_capability_catalog.md) documenting:
  - runtime precedence
  - covered providers
  - source families
  - operational caveats
- Updated [app/core/llm_utils.py](/Users/michael/work/nexus-agent/app/core/llm_utils.py):
  - new `EffectiveLLMSettings`
  - new `get_effective_llm_settings(...)`
  - runtime precedence is now:
    1. explicit config
    2. built-in catalog
    3. repository defaults
  - `build_token_budget(...)` now uses effective context/output limits
  - tokenizer resolution can now use catalog hints
- Updated [app/core/agent.py](/Users/michael/work/nexus-agent/app/core/agent.py) so the token-aware compact target uses the effective context window instead of only the static default.
- Extended [tests/unit/test_llm_utils_budget.py](/Users/michael/work/nexus-agent/tests/unit/test_llm_utils_budget.py) with catalog/override coverage.

## Decisions
- Kept explicit `LLM_CONTEXT_WINDOW`, `LLM_OUTPUT_WINDOW`, and `LLM_TOKENIZER` as the highest-priority runtime controls so operators can always override vendor defaults.
- Treated the built-in catalog as a practical runtime default layer, not a permanent source of truth, because vendor alias models can move over time.
- Limited tokenizer hints to cases where the app already standardizes on a concrete fallback rather than pretending every provider has an exact `tiktoken` mapping.

## Verification
- `uv run ruff check app/core/model_capabilities.py app/core/llm_utils.py app/core/agent.py tests/unit/test_llm_utils_budget.py`
  - passed
- `uv run pytest tests/unit/test_llm_utils_budget.py`
  - `6 passed`
