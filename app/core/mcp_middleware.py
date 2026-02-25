import hashlib
import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

SANDBOX_DATA_DIR = os.getenv("SANDBOX_DATA_DIR", "/app/storage/sandbox_data")


class MCPMiddleware:
    _cache: Dict[str, tuple[float, Any]] = {}
    _rate_limits: Dict[str, list[float]] = {}

    CACHE_TTL_DEFAULT = 300
    RATE_LIMIT_WINDOW = 1.0
    RATE_LIMIT_MAX = 5

    THRESHOLD_LOCAL_SMALL = 5_000
    THRESHOLD_LOCAL_LARGE = 30_000
    THRESHOLD_CLOUD_GLM = 400_000
    THRESHOLD_CLOUD_GEMINI = 3_000_000
    THRESHOLD_CLOUD_GPT = 200_000

    @classmethod
    def _get_response_threshold(cls) -> int:
        model_name = os.getenv("LLM_MODEL", "").lower()
        base_url = os.getenv("LLM_BASE_URL", "").lower()

        is_local = any(
            indicator in base_url for indicator in ["localhost", "127.0.0.1", "host.docker.internal", ":11434"]
        )

        if not is_local:
            if "gemini" in model_name or "flash" in model_name:
                return cls.THRESHOLD_CLOUD_GEMINI
            elif "glm-4" in model_name:
                return cls.THRESHOLD_CLOUD_GLM
            elif any(kw in model_name for kw in ["gpt-4", "claude"]):
                return cls.THRESHOLD_CLOUD_GPT

        if is_local and "glm-4" in model_name:
            return cls.THRESHOLD_LOCAL_LARGE

        return cls.THRESHOLD_LOCAL_SMALL

    @classmethod
    def _get_cache_key(cls, tool_name: str, args: dict, injected_keys: Optional[List[str]] = None) -> str:
        """Excludes injected secrets from the key to allow sharing results across users."""
        filtered_args = args.copy()
        if injected_keys:
            for key in injected_keys:
                filtered_args.pop(key, None)

        args_str = json.dumps(filtered_args, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    @classmethod
    async def _inject_user_secrets(cls, tool_name: str, args: dict, tool_config: Dict[str, Any]) -> List[str]:
        """Fetch user-level secrets from DB and inject into tool args for late-binding."""
        from sqlmodel import select

        from app.core.db import AsyncSessionLocal
        from app.core.security import decrypt_secret
        from app.models.secret import Secret, SecretScope

        plugin_id = tool_config.get("plugin_id")
        user_id = args.get("user_id")
        injected_keys = []

        if not plugin_id or not user_id:
            return injected_keys

        async with AsyncSessionLocal() as session:
            stmt = select(Secret).where(
                Secret.plugin_id == plugin_id, Secret.scope == SecretScope.user_scope, Secret.owner_id == user_id
            )
            result = await session.execute(stmt)
            secrets = result.scalars().all()

            for s in secrets:
                decrypted = decrypt_secret(s.encrypted_value)
                args[s.key] = decrypted
                injected_keys.append(s.key)
                logger.debug(f"Injected user secret '{s.key}' for tool '{tool_name}' (user_id={user_id})")

        return injected_keys

    @classmethod
    async def call_tool(
        cls, tool_name: str, args: dict, original_func: Callable, tool_config: Optional[Dict[str, Any]] = None
    ) -> Any:
        config = tool_config or {}
        ttl = config.get("cache_ttl", cls.CACHE_TTL_DEFAULT)

        now = time.time()
        if tool_name not in cls._rate_limits:
            cls._rate_limits[tool_name] = []

        cls._rate_limits[tool_name] = [t for t in cls._rate_limits[tool_name] if now - t < cls.RATE_LIMIT_WINDOW]

        if len(cls._rate_limits[tool_name]) >= cls.RATE_LIMIT_MAX:
            logger.warning(f"Rate limit hit for {tool_name}")
            return f"Rate limit exceeded for '{tool_name}'. Wait 1s."

        cls._rate_limits[tool_name].append(now)

        tool_args = args.copy()
        injected_keys = await cls._inject_user_secrets(tool_name, tool_args, config)
        cache_key = cls._get_cache_key(tool_name, args, injected_keys=None)  # args doesn't have secrets yet

        if ttl > 0 and cache_key in cls._cache:
            ts, cached_data = cls._cache[cache_key]
            if now - ts < ttl:
                logger.info(f"Cache HIT for {tool_name}")
                return cached_data

        try:
            if hasattr(original_func, "__call__"):
                result = await original_func(**tool_args)
            else:
                return f"Error: {original_func} is not callable."
        except Exception as e:
            logger.error(f"Tool error {tool_name}: {e}")
            return f"Error: {str(e)}"

        # Mask injected secrets in the result string to prevent leakage in cache or logs
        if injected_keys and isinstance(result, str):
            for k in injected_keys:
                secret_val = tool_args.get(k)
                if secret_val and isinstance(secret_val, str) and len(secret_val) >= 4:
                    result = result.replace(secret_val, "***MASKED***")

        is_wrapper = False
        parsed_wrapper = None

        if isinstance(result, str) and result.strip().startswith("{"):
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and "type" in parsed and "content" in parsed:
                    is_wrapper = True
                    parsed_wrapper = parsed
            except json.JSONDecodeError:
                pass

        result_str = str(result)
        result_len = len(result_str)
        threshold = cls._get_response_threshold()

        if result_len > threshold:
            logger.info(f"Response too large ({result_len} chars, threshold={threshold}). Offloading...")
            os.makedirs(SANDBOX_DATA_DIR, exist_ok=True)

            if is_wrapper and parsed_wrapper:
                data_to_save = parsed_wrapper["content"]
            else:
                data_to_save = result

            is_structured = isinstance(data_to_save, (dict, list))

            if not is_structured and isinstance(data_to_save, str) and data_to_save.strip().startswith(("{", "[")):
                content_stripped = data_to_save.strip()
                try:
                    data_to_save = json.loads(content_stripped)
                    is_structured = True
                except json.JSONDecodeError:
                    if content_stripped.count("}{") > 0:
                        try:
                            wrapped = "[" + content_stripped.replace("}\n{", "},{").replace("}{", "},{") + "]"
                            data_to_save = json.loads(wrapped)
                            is_structured = True
                            logger.info("Successfully recovered JSONL data by wrapping in array")
                        except Exception:
                            pass

            ext = ".json" if is_structured else ".txt"
            filename = f"tool_output_{cache_key[:8]}_{int(now)}{ext}"
            filepath = os.path.join(SANDBOX_DATA_DIR, filename)

            try:
                with open(filepath, "w") as f:
                    if is_structured:
                        json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                    else:
                        f.write(str(data_to_save))

                preview = ""
                if not is_structured:
                    preview_text = str(data_to_save)[:300].replace("\n", "\\n")
                    preview = f"PREVIEW: {preview_text}..."

                if is_structured:
                    message_content = (
                        f"FORMAT: JSON (List/Dict). \n"
                        f"ACTION: Write Python code using `json.load(open('{filepath}'))`.\n"
                        f"FILTER_LOGIC: Match `entity_id` or `attributes.friendly_name` using `.lower()`."
                    )
                else:
                    message_content = (
                        f"FORMAT: UNSTRUCTURED TEXT.\n"
                        f"PREVIEW: {preview}\n"
                        f"ACTION: Read file: `text = open('{filepath}').read()`.\n"
                        f"PARSING: Check the preview above. Valid strategies:\n"
                        f"  - Line-based: `for line in text.split('\\n'):`\n"
                        f"  - Regex: `re.findall(r'...', text)`\n"
                        f"RETURN: List of matching items.\n"
                    )

                alert_text = (
                    f"SYSTEM_ALERT: OUTPUT_TOO_LARGE ({result_len} bytes). "
                    f"Data saved to: '{filepath}'.\n"
                    f"{message_content}"
                )

                result = json.dumps({"type": "text", "content": alert_text}, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Offload failed: {e}")
                result = result_str[:2000] + "\n[Truncated]"

        if ttl > 0:
            cls._cache[cache_key] = (now, result)

        return result
