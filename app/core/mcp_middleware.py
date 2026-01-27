import logging
import time
import json
import hashlib
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

SANDBOX_DATA_DIR = "/app/storage/sandbox_data"

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

        result_str = str(result)
        result_len = len(result_str)
        
        if result_len > cls.LARGE_RESPONSE_THRESHOLD:
            logger.info(f"Response too large ({result_len} chars). Offloading...")
            os.makedirs(SANDBOX_DATA_DIR, exist_ok=True)
            
            is_structured = isinstance(result, (dict, list))
            ext = ".json" if is_structured else ".txt"
            filename = f"tool_output_{cache_key[:8]}_{int(now)}{ext}"
            filepath = os.path.join(SANDBOX_DATA_DIR, filename)
            
            try:
                with open(filepath, "w") as f:
                    if is_structured:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    else:
                        f.write(result_str)
                
                read_code = f"json.load(open('{filepath}'))" if is_structured else f"open('{filepath}').read()"
                
                # Minimal format with markers for parsing
                result = (
                    f"<<<OFFLOAD|{filepath}|{result_len//1000}KB>>>\n"
                    f"<<<CODE>>>\n"
                    f"d={read_code}\n"
                    f"for l in str(d).split('\\n')[:30]:print(l)\n"
                    f"<<<END>>>\n"
                    f"SYSTEM: You MUST execute the code block above using `python_sandbox`."
                )
            except Exception as e:
                logger.error(f"Offload failed: {e}")
                result = result_str[:2000] + "\n[Truncated]"

        if ttl > 0:
            cls._cache[cache_key] = (now, result)
            
        return result
