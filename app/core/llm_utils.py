import logging
import os
from typing import Any

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

logger = logging.getLogger("nexus.llm_utils")


def get_httpx_timeout() -> httpx.Timeout:
    """Returns a robust timeout for LLM/Embedding calls."""
    return httpx.Timeout(60.0, connect=10.0)


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


def get_llm_client(temperature: float = 0) -> ChatOpenAI:
    """Configures and returns the LLM instance based on environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model_name = os.getenv("LLM_MODEL", "gpt-4o")

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
