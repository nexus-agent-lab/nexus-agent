import logging
import time
import json
import hashlib
import os
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Sandbox data path (must be mounted in docker-compose)
SANDBOX_DATA_DIR = "/app/storage/sandbox_data"

class MCPMiddleware:
    """
    Middleware layer for MCP Tool calls.
    Features:
    1. Global Caching (Shared across users)
    2. Rate Limiting
    3. Big Data Offloading (Offloader Pattern)
    """
    
    # Simple in-memory cache: { "hash_key": (timestamp, data) }
    _cache: Dict[str, tuple[float, Any]] = {}
    
    # Rate limits: { "tool_name": [timestamp1, timestamp2, ...] }
    _rate_limits: Dict[str, list[float]] = {}
    
    # Configuration (Dynamic)
    CACHE_TTL_DEFAULT = 300  # 5 minutes
    
    RATE_LIMIT_WINDOW = 1.0
    RATE_LIMIT_MAX = 5
    
    LARGE_RESPONSE_THRESHOLD = 5000 # 5KB

    @classmethod
    def _get_cache_key(cls, tool_name: str, args: dict) -> str:
        # Sort args to ensure stable hash
        args_str = json.dumps(args, sort_keys=True)
        return f"{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    @classmethod
    async def call_tool(cls, tool_name: str, args: dict, original_func: Callable, tool_config: dict = None) -> Any:
        
        # Determine TTL from config or default
        tool_config = tool_config or {}
        ttl = tool_config.get("cache_ttl", cls.CACHE_TTL_DEFAULT)

        now = time.time()
        if tool_name not in cls._rate_limits:
            cls._rate_limits[tool_name] = []
        
        # Clean old timestamps
        cls._rate_limits[tool_name] = [t for t in cls._rate_limits[tool_name] if now - t < cls.RATE_LIMIT_WINDOW]
        
        if len(cls._rate_limits[tool_name]) >= cls.RATE_LIMIT_MAX:
            logger.warning(f"Rate limit hit for {tool_name}")
            return f"System Alert: Rate limit exceeded for tool '{tool_name}'. Please wait 1 second."
        
        if len(cls._rate_limits[tool_name]) >= cls.RATE_LIMIT_MAX:
            logger.warning(f"Rate limit hit for {tool_name}")
            return f"System Alert: Rate limit exceeded for tool '{tool_name}'. Please wait 1 second."
        
        cls._rate_limits[tool_name].append(now)

        # --- 2. Cache Read ---
        cache_key = cls._get_cache_key(tool_name, args)
        
        if ttl > 0:
            if cache_key in cls._cache:
                ts, cached_data = cls._cache[cache_key]
                # Check expiry
                if now - ts < ttl:
                    logger.info(f"Cache HIT for {tool_name} (TTL={ttl}s)")
                    return cached_data

        # --- 3. Execute Real Tool ---
        try:
            # Check if original_func is async or sync 
            # (Assuming standard MCP tools are async mostly, but verify)
            if hasattr(original_func, "__call__"):
                 if os.environ.get("DEBUG_MCP"):
                     logger.info(f"Executing {tool_name} with args: {args}")
                 
                 # In standard invoke, we just run it. 
                 # Depending on how 'original_func' is passed (run function vs bound tool)
                 # We assume it's a coroutine function or awaitable
                 result = await original_func(**args)
            else:
                return f"Error: Tool execution failed. {original_func} is not callable."

        except Exception as e:
            logger.error(f"Tool execution error {tool_name}: {e}")
            return f"Error executing tool {tool_name}: {str(e)}"

        # --- 4. Offloading (Big Data Governor) ---
        result_str = str(result)
        result_len = len(result_str)
        
        if result_len > cls.LARGE_RESPONSE_THRESHOLD:
            logger.info(f"Response too large ({result_len} chars). Offloading...")
            
            # Ensure directory exists
            os.makedirs(SANDBOX_DATA_DIR, exist_ok=True)
            
            # Generate filename
            filename = f"tool_output_{cache_key[:8]}_{int(now)}.json"
            filepath = os.path.join(SANDBOX_DATA_DIR, filename)
            
            # Save to file
            try:
                with open(filepath, "w") as f:
                    # Try to dump as JSON pretty print if possible for readability
                    if isinstance(result, (dict, list)):
                        json.dump(result, f, indent=2)
                    else:
                        f.write(result_str)
                
                # Generate Preview
                preview = "Data Preview: "
                if isinstance(result, list):
                    preview += json.dumps(result[:2], ensure_ascii=False)
                elif isinstance(result, dict):
                    keys = list(result.keys())[:5]
                    preview += f"Keys: {keys}"
                else:
                    preview += result_str[:200]
                
                # Construct Mock Response
                result = (
                    f"SYSTEM_ALERT: OUTPUT_TOO_LARGE ({result_len} bytes). "
                    f"The raw data has been saved to file: '{filepath}'. \n"
                    f"{preview}...\n"
                    "MANDATORY ACTION: You CANNOT see the full data. "
                    "Call `python_sandbox` to read this file and filter it."
                )
            except Exception as e:
                logger.error(f"Failed to offload data: {e}")
                # Fallback: simple truncation
                result = result_str[:2000] + "\n[Truncated due to error in offloading]"

        # --- 5. Cache Write ---
        if ttl > 0:
            cls._cache[cache_key] = (now, result)
            
        return result
