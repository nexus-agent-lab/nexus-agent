import logging
import os

import httpx

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
    # Debug logging for Proxy usage
    proxy = None
    trust_env = True  # Default behavior

    # Check bypass first
    if base_url and is_local_url(base_url):
        logger.debug(f"Local URL detected ({base_url}). Disabling proxy (trust_env=False).")
        trust_env = False
        # Do not check for fallback proxies as we want direct connection

    elif os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        logger.debug("Creating httpx.Client with system proxy detected.")
    elif os.getenv("TELEGRAM_PROXY_URL"):
        # Fallback: Use Telegram proxy if set (User likely has one global proxy)
        p = os.getenv("TELEGRAM_PROXY_URL")
        # Safety check: httpx only supports http/https without extra deps
        if p.startswith("http://") or p.startswith("https://"):
            proxy = p
            logger.info(f"Creating httpx.Client using fallback TELEGRAM_PROXY_URL: {p}")
        else:
            logger.warning(f"TELEGRAM_PROXY_URL is set but not used for LLM (unsupported scheme in httpx): {p}")
            logger.info("Tip: LLM calls will try direct connection. If blocked, set HTTP_PROXY.")

    return httpx.Client(timeout=get_httpx_timeout(), trust_env=trust_env, proxy=proxy, event_hooks=event_hooks)


def get_httpx_async_client(event_hooks: dict = None, base_url: str = None) -> httpx.AsyncClient:
    """
    Returns a robust async httpx.AsyncClient with standard Nexus configuration.
    Sets timeout and trust_env based on target URL.
    """
    # Debug logging for Proxy usage
    proxy = None
    trust_env = True  # Default behavior

    # Check bypass
    if base_url and is_local_url(base_url):
        logger.debug(f"Local URL detected ({base_url}). Disabling proxy (trust_env=False).")
        trust_env = False

    elif os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        pass  # trust_env will handle it
    elif os.getenv("TELEGRAM_PROXY_URL"):
        # Fallback: Use Telegram proxy if set
        p = os.getenv("TELEGRAM_PROXY_URL")
        if p.startswith("http://") or p.startswith("https://"):
            proxy = p
            logger.info(f"Creating httpx.AsyncClient using fallback TELEGRAM_PROXY_URL: {p}")

    return httpx.AsyncClient(timeout=get_httpx_timeout(), trust_env=trust_env, proxy=proxy, event_hooks=event_hooks)
