import asyncio
import logging

from app.core.mcp_manager import _mcp_manager

logging.basicConfig(level=logging.INFO)


async def test():
    # Force _load_from_db to return {}
    _mcp_manager._load_from_db = lambda: asyncio.sleep(0) or {}
    await _mcp_manager.initialize()
    print("Tools loaded:", len(_mcp_manager.get_tools()))
    print("Config used:", _mcp_manager._config)


if __name__ == "__main__":
    asyncio.run(test())
