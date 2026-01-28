import logging
import time
import json
import hashlib
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

SANDBOX_DATA_DIR = os.getenv("SANDBOX_DATA_DIR", "/app/storage/sandbox_data")

class MCPMiddleware:
    _cache: Dict[str, tuple[float, Any]] = {}
    _rate_limits: Dict[str, list[float]] = {}
    
    CACHE_TTL_DEFAULT = 300
    RATE_LIMIT_WINDOW = 1.0
    RATE_LIMIT_MAX = 5
    LARGE_RESPONSE_THRESHOLD = 5000

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
        
        if result_len > cls.LARGE_RESPONSE_THRESHOLD:
            logger.info(f"Response too large ({result_len} chars). Offloading...")
            os.makedirs(SANDBOX_DATA_DIR, exist_ok=True)
            
            # Determine effective content to save
            if is_wrapper and parsed_wrapper:
                data_to_save = parsed_wrapper["content"]
            else:
                data_to_save = result

            # Detect structure of the DATA to save (not the wrapper)
            is_structured = isinstance(data_to_save, (dict, list))
            
            # Additional check: If data_to_save is a string but likely JSON
            if not is_structured and isinstance(data_to_save, str) and data_to_save.strip().startswith(("{", "[")):
                try:
                    data_to_save = json.loads(data_to_save)
                    is_structured = True
                except json.JSONDecodeError:
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
                result = json.dumps({
                    "type": "text", 
                    "content": alert_text
                }, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Offload failed: {e}")
                # Fallback
                result = result_str[:2000] + "\n[Truncated]"

        if ttl > 0:
            cls._cache[cache_key] = (now, result)
            
        return result
