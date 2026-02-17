import hashlib
import json
import logging
import os
import time
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

SANDBOX_DATA_DIR = os.getenv("SANDBOX_DATA_DIR", "/app/storage/sandbox_data")


class MCPMiddleware:
    _cache: Dict[str, tuple[float, Any]] = {}
    _rate_limits: Dict[str, list[float]] = {}

    CACHE_TTL_DEFAULT = 300
    RATE_LIMIT_WINDOW = 1.0
    RATE_LIMIT_MAX = 5

    # Dynamic thresholds based on model capabilities and deployment
    # Format: (chars) ≈ tokens × 3-4 for estimation
    THRESHOLD_LOCAL_SMALL = 5_000  # Local small models: ~1.2k tokens
    THRESHOLD_LOCAL_LARGE = 30_000  # Local GLM-4.7: ~8k tokens (保守，避免推理慢)
    THRESHOLD_CLOUD_GLM = 400_000  # Cloud GLM-4.7 (128k context): ~100k tokens
    THRESHOLD_CLOUD_GEMINI = 3_000_000  # Cloud Gemini Flash (1M context): ~750k tokens
    THRESHOLD_CLOUD_GPT = 200_000  # Cloud GPT-4/Claude: ~50k tokens

    @classmethod
    def _get_response_threshold(cls) -> int:
        """
        Dynamically determine response threshold based on:
        1. Deployment location (local vs cloud)
        2. Model type and capabilities
        """
        model_name = os.getenv("LLM_MODEL", "").lower()
        base_url = os.getenv("LLM_BASE_URL", "").lower()

        # Detect local deployment
        is_local = any(
            indicator in base_url for indicator in ["localhost", "127.0.0.1", "host.docker.internal", ":11434"]
        )

        # Cloud models with massive context
        if not is_local:
            if "gemini" in model_name or "flash" in model_name:
                logger.debug("Cloud Gemini Flash detected: using 3M char threshold")
                return cls.THRESHOLD_CLOUD_GEMINI
            elif "glm-4" in model_name:
                logger.debug("Cloud GLM-4.7 detected: using 400k char threshold")
                return cls.THRESHOLD_CLOUD_GLM
            elif any(kw in model_name for kw in ["gpt-4", "claude"]):
                logger.debug("Cloud GPT-4/Claude detected: using 200k char threshold")
                return cls.THRESHOLD_CLOUD_GPT

        # Local large context models (need conservative limits)
        if is_local and "glm-4" in model_name:
            logger.debug("Local GLM-4.7 detected: using 30k char threshold")
            return cls.THRESHOLD_LOCAL_LARGE

        # Default: small local models
        logger.debug("Default small model threshold: 5k chars")
        return cls.THRESHOLD_LOCAL_SMALL

    @classmethod
    def _get_cache_key(cls, tool_name: str, args: dict) -> str:
        args_str = json.dumps(args, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    @classmethod
    async def call_tool(cls, tool_name: str, args: dict, original_func: Callable, tool_config: dict = None) -> Any:
        tool_config = tool_config or {}
        ttl = tool_config.get("cache_ttl", cls.CACHE_TTL_DEFAULT)

        now = time.time()
        if tool_name not in cls._rate_limits:
            cls._rate_limits[tool_name] = []

        cls._rate_limits[tool_name] = [t for t in cls._rate_limits[tool_name] if now - t < cls.RATE_LIMIT_WINDOW]

        if len(cls._rate_limits[tool_name]) >= cls.RATE_LIMIT_MAX:
            logger.warning(f"Rate limit hit for {tool_name}")
            return f"Rate limit exceeded for '{tool_name}'. Wait 1s."

        cls._rate_limits[tool_name].append(now)

        cache_key = cls._get_cache_key(tool_name, args)

        if ttl > 0 and cache_key in cls._cache:
            ts, cached_data = cls._cache[cache_key]
            if now - ts < ttl:
                logger.info(f"Cache HIT for {tool_name}")
                return cached_data

        try:
            if hasattr(original_func, "__call__"):
                result = await original_func(**args)
            else:
                return f"Error: {original_func} is not callable."
        except Exception as e:
            logger.error(f"Tool error {tool_name}: {e}")
            return f"Error: {str(e)}"

        # Helper: Extract unified wrapper content if present (Moltbot architecture)
        is_wrapper = False
        parsed_wrapper = None

        # Check if result is a JSON string of our wrapper
        if isinstance(result, str) and result.strip().startswith("{"):
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and "type" in parsed and "content" in parsed:
                    is_wrapper = True
                    parsed_wrapper = parsed
                    # Unwrap logic: If valid wrapper, we want to offload the CONTENT, not the wrapper itself
                    # But we must be careful: if we return unwrapped content here, we break the contract
                    # that mcp.py ALWAYS returns a JSON string.
                    # Wait, middleware returns to mcp.py? No, mcp.py calls middleware.
                    # mcp.py: return await Middleware.call_tool(..., original_func=unwrapped_logic)
                    # So original_func returns the JSON string wrapper.
                    # If we return a dict here, mcp.py wrapper logic is bypassed?
                    # No, mcp.py's `original_mcp_call` IS the `original_func` passed here.
                    # So `result` IS the JSON string wrapper from mcp.py.
                    pass
            except json.JSONDecodeError:
                pass

        # Improve Large Response Handling
        result_str = str(result)
        result_len = len(result_str)

        # Use dynamic threshold based on model capabilities
        threshold = cls._get_response_threshold()

        if result_len > threshold:
            logger.info(f"Response too large ({result_len} chars, threshold={threshold}). Offloading...")
            os.makedirs(SANDBOX_DATA_DIR, exist_ok=True)

            # Determine effective content to save
            if is_wrapper and parsed_wrapper:
                data_to_save = parsed_wrapper["content"]
            else:
                data_to_save = result

            # Detect structure of the DATA to save (not the wrapper)
            is_structured = isinstance(data_to_save, (dict, list))

            # Additional check: If data_to_save is a string but likely JSON or JSONL (multiple objects)
            if not is_structured and isinstance(data_to_save, str) and data_to_save.strip().startswith(("{", "[")):
                content_stripped = data_to_save.strip()
                try:
                    data_to_save = json.loads(content_stripped)
                    is_structured = True
                except json.JSONDecodeError:
                    # Attempt to handle JSONL (multiple concatenated objects)
                    # Common in list_entities output from HA
                    if content_stripped.count("}{") > 0:
                        try:
                            # Wrap in [ ] and add commas between objects
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

                # Enhanced System Alert: "Teacher Mode" with Preview
                preview = ""
                if not is_structured:
                    # Provide a preview to help LLM write the regex
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

                # Return a format that implies this is the "new" result
                # NOTE: If the original caller expects the JSON wrapper string, we should respect that.
                # But here we are replacing the result with a System Alert.
                # We should probably wrap the System Alert in the Unified Wrapper format too?
                # "type": "error" or "text" so Agent can read it.
                # Actually, System Alert is usually treated as Text by the Agent.
                # But strict Agent expects JSON wrapper?
                # Let's check agent.py: "Always parse the `content` field."
                # So we should wrap this alert in {type: "text", content: ...}

                alert_text = (
                    f"SYSTEM_ALERT: OUTPUT_TOO_LARGE ({result_len} bytes). "
                    f"Data saved to: '{filepath}'.\n"
                    f"{message_content}"
                )

                # Wrap it so Agent parses it correctly
                result = json.dumps({"type": "text", "content": alert_text}, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Offload failed: {e}")
                # Fallback
                result = result_str[:2000] + "\n[Truncated]"

        if ttl > 0:
            cls._cache[cache_key] = (now, result)

        return result
