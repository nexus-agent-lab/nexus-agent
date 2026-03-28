import asyncio
import logging
import os
import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx
import openai
import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.core.model_capabilities import lookup_model_capability

logger = logging.getLogger("nexus.llm_utils")
_TOKENIZER_FALLBACK_WARNED: set[str] = set()


@dataclass
class TokenBudget:
    estimated_input_tokens: int
    remaining_input_budget: int
    near_context_limit: bool
    can_afford_structured_postprocess: bool
    degraded: bool = False


@dataclass(frozen=True)
class EffectiveLLMSettings:
    model_name: str
    context_window: int
    output_window: int
    tokenizer: str | None = None
    source: str = "default"


def get_httpx_timeout() -> httpx.Timeout:
    """Returns a robust timeout for LLM/Embedding calls."""
    return httpx.Timeout(60.0, connect=10.0)


def _is_rate_limit_error(exc: Exception) -> bool:
    if isinstance(exc, openai.RateLimitError):
        return True

    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True

    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True

    message = str(exc).lower()
    return "rate limit" in message or "速率限制" in message or "429" in message


async def ainvoke_with_backoff(llm: Any, messages: Any, *, operation_name: str = "llm") -> Any:
    """
    Invoke an LLM with explicit 429 backoff handling.

    The upstream SDK may already do short retries, but some providers need a
    slower pause before the next attempt will succeed.
    """
    attempts = max(1, int(settings.LLM_RATE_LIMIT_RETRIES))
    base_delay = max(0.1, float(settings.LLM_RATE_LIMIT_BASE_DELAY_SECONDS))
    max_delay = max(base_delay, float(settings.LLM_RATE_LIMIT_MAX_DELAY_SECONDS))

    for attempt in range(1, attempts + 1):
        try:
            return await llm.ainvoke(messages)
        except Exception as exc:
            if not _is_rate_limit_error(exc) or attempt >= attempts:
                raise

            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0, min(1.0, delay * 0.1))
            logger.warning(
                "Rate limited during %s (attempt %d/%d). Sleeping %.2fs before retry.",
                operation_name,
                attempt,
                attempts,
                delay,
            )
            await asyncio.sleep(delay)


def estimate_message_tokens(messages: list[Any] | None) -> int:
    total = 0
    for msg in messages or []:
        content = str(getattr(msg, "content", "") or "")
        total += max(1, len(content) // 4) + 8
    return total


def _is_setting_explicit(field_name: str) -> bool:
    return field_name in getattr(settings, "model_fields_set", set()) or field_name in os.environ


def get_active_llm_model_name(model_name: str | None = None) -> str:
    return model_name if model_name is not None else os.getenv("LLM_MODEL", settings.LLM_MODEL)


def get_effective_llm_settings(model_name: str | None = None) -> EffectiveLLMSettings:
    active_model = get_active_llm_model_name(model_name)
    capability = lookup_model_capability(active_model)

    explicit_context = _is_setting_explicit("LLM_CONTEXT_WINDOW")
    explicit_output = _is_setting_explicit("LLM_OUTPUT_WINDOW")
    explicit_tokenizer = _is_setting_explicit("LLM_TOKENIZER")

    context_window = (
        int(settings.LLM_CONTEXT_WINDOW)
        if explicit_context
        else int(capability.context_window if capability else settings.LLM_CONTEXT_WINDOW)
    )
    output_window = (
        int(settings.LLM_OUTPUT_WINDOW)
        if explicit_output
        else int(
            capability.max_output_tokens if capability and capability.max_output_tokens else settings.LLM_OUTPUT_WINDOW
        )
    )
    tokenizer = settings.LLM_TOKENIZER if explicit_tokenizer else (capability.tokenizer if capability else None)

    if explicit_context or explicit_output or explicit_tokenizer:
        source = "explicit"
    elif capability:
        source = "catalog"
    else:
        source = "default"

    return EffectiveLLMSettings(
        model_name=active_model,
        context_window=context_window,
        output_window=output_window,
        tokenizer=tokenizer,
        source=source,
    )


def _resolve_tokenizer_name(model_name: str | None = None) -> str:
    effective = get_effective_llm_settings(model_name)
    configured = (effective.tokenizer or "").strip()
    if configured:
        return configured
    return effective.model_name


def _alias_tokenizer_name(tokenizer_name: str) -> str:
    lowered = (tokenizer_name or "").strip().lower()
    if lowered.startswith("glm-"):
        return "cl100k_base"
    return tokenizer_name


@lru_cache(maxsize=32)
def _encoding_for_model(model_name: str | None = None):
    tokenizer_name = _resolve_tokenizer_name(model_name)
    aliased_name = _alias_tokenizer_name(tokenizer_name)

    if aliased_name != tokenizer_name:
        return tiktoken.get_encoding(aliased_name), False

    try:
        return tiktoken.get_encoding(tokenizer_name), False
    except Exception:
        pass

    try:
        return tiktoken.encoding_for_model(tokenizer_name), False
    except Exception:
        if tokenizer_name not in _TOKENIZER_FALLBACK_WARNED:
            logger.warning("Falling back to cl100k_base tokenizer for model=%s", tokenizer_name)
            _TOKENIZER_FALLBACK_WARNED.add(tokenizer_name)
        return tiktoken.get_encoding("cl100k_base"), True


def count_text_tokens(text: str, model_name: str | None = None) -> tuple[int, bool]:
    if not text:
        return 0, False

    try:
        encoding, degraded = _encoding_for_model(model_name)
        return len(encoding.encode(text)), degraded
    except Exception:
        return max(1, len(text) // 4), True


def count_prompt_tokens(messages: list[BaseMessage] | None, model_name: str | None = None) -> tuple[int, bool]:
    if not messages:
        return 0, False

    degraded = False
    total = 0
    for msg in messages:
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        elif isinstance(msg, ToolMessage):
            role = "tool"
        else:
            role = getattr(msg, "type", "user")

        role_tokens, role_degraded = count_text_tokens(role, model_name=model_name)
        content_tokens, content_degraded = count_text_tokens(
            str(getattr(msg, "content", "") or ""), model_name=model_name
        )
        total += role_tokens + content_tokens + 6
        degraded = degraded or role_degraded or content_degraded

    total += 3
    return total, degraded


def build_token_budget(messages: list[BaseMessage] | None, model_name: str | None = None) -> TokenBudget:
    estimated_input_tokens, degraded = count_prompt_tokens(messages, model_name=model_name)
    effective = get_effective_llm_settings(model_name)
    context_window = max(1, int(effective.context_window))
    remaining_input_budget = max(0, context_window - estimated_input_tokens)
    near_context_limit = estimated_input_tokens >= int(context_window * float(settings.LLM_CONTEXT_SOFT_LIMIT_RATIO))
    can_afford_structured_postprocess = remaining_input_budget >= max(4096, int(effective.output_window * 0.1))
    return TokenBudget(
        estimated_input_tokens=estimated_input_tokens,
        remaining_input_budget=remaining_input_budget,
        near_context_limit=near_context_limit,
        can_afford_structured_postprocess=can_afford_structured_postprocess,
        degraded=degraded,
    )


def build_large_output_guidance(messages: list[Any] | None) -> str | None:
    latest_large_output: ToolMessage | None = None
    for msg in reversed(messages or []):
        if isinstance(msg, ToolMessage) and "SYSTEM_ALERT: OUTPUT_TOO_LARGE" in str(msg.content):
            latest_large_output = msg
            break

    if latest_large_output is None:
        return None

    content = str(latest_large_output.content)
    effective = get_effective_llm_settings()
    budget = build_token_budget(messages, model_name=effective.model_name)
    usage_ratio = budget.estimated_input_tokens / max(1, int(effective.context_window))
    tool_name = getattr(latest_large_output, "name", "") or "unknown_tool"
    is_browser = tool_name.startswith("browser_")
    is_unstructured = "FORMAT: UNSTRUCTURED TEXT" in content

    if is_browser and is_unstructured:
        if budget.near_context_limit:
            return (
                "Recent browser output was truncated and is unstructured text. "
                f"Estimated context usage is already about {usage_ratio:.0%} of the model window. "
                "Do not call `python_sandbox` just to load or parse the full browser artifact. "
                "Instead narrow the browser request: refine the URL/query, read a smaller section, "
                "or summarize only from the previewed evidence."
            )
        return (
            "Recent browser output was truncated and is unstructured text. "
            "Prefer a narrower browser-side follow-up first. "
            "Use `python_sandbox` only if the user needs real computation, deduping, or structured parsing "
            "and the current token budget still leaves room for a compact structured post-process."
        )

    if budget.near_context_limit:
        return (
            f"Recent tool output was truncated and estimated context usage is about {usage_ratio:.0%} "
            "of the model window. Prefer the smallest next step possible and avoid loading full artifacts "
            "into `python_sandbox` unless structured processing is truly required."
        )

    return None


def is_local_url(url: str) -> bool:
    """Checks if the URL is local (localhost, 127.0.0.1, host.docker.internal)."""
    if not url:
        return False
    # Simple check for common local domains
    if "localhost" in url or "127.0.0.1" in url or "host.docker.internal" in url:
        return True
    return False


def get_httpx_client(event_hooks: dict = None, base_url: str = None) -> httpx.Client:
    """
    Returns a robust sync httpx.Client with standard Nexus configuration.
    Sets timeout and trust_env based on target URL.
    """
    proxy = None
    trust_env = True

    if base_url and is_local_url(base_url):
        logger.debug(f"Local URL detected ({base_url}). Disabling proxy (trust_env=False).")
        trust_env = False
    elif os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        logger.debug("Creating httpx.Client with system proxy detected.")
    elif os.getenv("TELEGRAM_PROXY_URL"):
        p = os.getenv("TELEGRAM_PROXY_URL")
        if p.startswith("http://") or p.startswith("https://"):
            proxy = p
            logger.info(f"Creating httpx.Client using fallback TELEGRAM_PROXY_URL: {p}")
        else:
            logger.warning(f"TELEGRAM_PROXY_URL is set but not used for LLM: {p}")

    return httpx.Client(timeout=get_httpx_timeout(), trust_env=trust_env, proxy=proxy, event_hooks=event_hooks)


def get_httpx_async_client(event_hooks: dict = None, base_url: str = None) -> httpx.AsyncClient:
    """
    Returns a robust async httpx.AsyncClient with standard Nexus configuration.
    Sets timeout and trust_env based on target URL.
    """
    proxy = None
    trust_env = True

    if base_url and is_local_url(base_url):
        logger.debug(f"Local URL detected ({base_url}). Disabling proxy (trust_env=False).")
        trust_env = False
    elif os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        pass  # trust_env will handle it
    elif os.getenv("TELEGRAM_PROXY_URL"):
        p = os.getenv("TELEGRAM_PROXY_URL")
        if p.startswith("http://") or p.startswith("https://"):
            proxy = p
            logger.info(f"Creating httpx.AsyncClient using fallback TELEGRAM_PROXY_URL: {p}")

    return httpx.AsyncClient(timeout=get_httpx_timeout(), trust_env=trust_env, proxy=proxy, event_hooks=event_hooks)


def get_llm_client(
    temperature: float = 0,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model_name: str | None = None,
) -> ChatOpenAI:
    """Configures and returns the LLM instance based on environment variables."""
    api_key = api_key if api_key is not None else os.getenv("LLM_API_KEY")
    base_url = base_url if base_url is not None else os.getenv("LLM_BASE_URL")
    model_name = model_name if model_name is not None else os.getenv("LLM_MODEL", "gpt-4o")

    logger.info(f"Initializing LLM client: base_url={base_url}, model={model_name}, temp={temperature}")

    if not api_key:
        logger.warning("LLM_API_KEY is not set.")

    # Optimized config for GLM-4.7-Flash
    if "glm-4" in model_name.lower() and "flash" in model_name.lower():
        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=max(temperature, 0.1),
            streaming=False,
        )

    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        streaming=False,
    )


def get_embeddings_client() -> Any:
    """
    Returns a configured embedding model instance.
    Handles Ollama, Local Server (9292), and OpenAI-compatible providers.
    """
    base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL")
    api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY")

    # Defaults
    default_model = "embedding-3" if base_url and "bigmodel" in base_url else "text-embedding-3-small"
    model_name = os.getenv("EMBEDDING_MODEL", default_model)
    dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))

    logger.info(f"Initializing Embeddings client: base_url='{base_url}', model='{model_name}'")

    if not base_url:
        logger.warning("No EMBEDDING_BASE_URL or LLM_BASE_URL found. Falling back to default OpenAI.")
        return OpenAIEmbeddings(model=model_name, api_key=api_key)

    # Use OllamaEmbeddings for Ollama backend (port 11434)
    if "11434" in base_url:
        from langchain_ollama import OllamaEmbeddings

        ollama_base = base_url.replace("/v1", "").rstrip("/")
        return OllamaEmbeddings(
            model=model_name.replace(":latest", ""),
            base_url=ollama_base,
        )

    # Local custom embedding server (e.g. bge-micro-v2)
    if "9292" in base_url:
        return OpenAIEmbeddings(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            check_embedding_ctx_length=False,
        )

    # Default: OpenAI or compatible
    return OpenAIEmbeddings(
        model=model_name,
        api_key=api_key,
        base_url=base_url,
        dimensions=dimension if dimension == 1536 else None,
    )
