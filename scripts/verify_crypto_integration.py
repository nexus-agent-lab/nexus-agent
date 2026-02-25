import asyncio
import logging

from sqlalchemy import select

from app.core.db import AsyncSessionLocal, init_db
from app.core.mcp_manager import MCPManager
from app.models.plugin import Plugin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_crypto_integration():
    """
    Registers the Crypto Trading Assistant plugin in the database
    and verifies that the MCP Manager can discover its tools.
    """
    # Initialize the database connection
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if the plugin already exists to avoid duplicates
        stmt = select(Plugin).where(Plugin.name == "Crypto Trading Assistant")
        result = await session.execute(stmt)
        existing_plugin = result.scalars().first()
        if existing_plugin:
            logger.info("Plugin 'Crypto Trading Assistant' already exists in the database. Updating config...")
            existing_plugin.type = "mcp_stdio"
            existing_plugin.source_url = ""
            existing_plugin.status = "active"
            existing_plugin.config = {"command": "python3", "args": ["/Users/michael/work/crypto-bot/mcp_server.py"]}
        else:
            logger.info("Registering 'Crypto Trading Assistant' plugin in the database...")
            new_plugin = Plugin(
                name="Crypto Trading Assistant",
                type="mcp_stdio",
                source_url="",
                status="active",
                config={"command": "python3", "args": ["/Users/michael/work/crypto-bot/mcp_server.py"]},
            )
            session.add(new_plugin)
        await session.commit()
        logger.info("Plugin registration committed to the database.")

    # Initialize or Reload the MCP Manager
    mcp = MCPManager.get_instance()
    await mcp.reload()

    # Verify tools
    tools = mcp.get_tools()
    tool_names = [tool.name for tool in tools]

    logger.info(f"Discovered {len(tools)} tools after reload.")
    logger.info(f"Tool names: {tool_names}")
    crypto_tools_found = any(
        name in ["get_klines", "get_account_info", "get_my_trades", "get_open_orders"] for name in tool_names
    )
    if crypto_tools_found:
        logger.info("SUCCESS: Crypto bot tools were successfully discovered and loaded via the DB!")
    else:
        logger.error("FAILURE: Crypto bot tools were not found in the MCP Manager.")

    await mcp.cleanup()


if __name__ == "__main__":
    asyncio.run(verify_crypto_integration())
