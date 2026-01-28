import asyncio
import logging
import json
import os
import sys

# Ensure app is in path
sys.path.append(os.getcwd())

from app.core.mcp_manager import MCPManager as ProcessManager
from app.core.mcp import get_mcp_tools

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_ha")

async def main():
    logger.info("--- Phase 1: Starting MCP Processes ---")
    ProcessManager.start_all()
    
    # Give them a moment to spin up
    await asyncio.sleep(2)
    
    logger.info("--- Phase 2: Connecting Client & Loading Tools ---")
    try:
        tools = await get_mcp_tools()
        logger.info(f"Loaded {len(tools)} tools: {[t.name for t in tools]}")
    except Exception as e:
        logger.error(f"Failed to load tools: {e}")
        ProcessManager.stop_all()
        return

    # Find HA tools
    # Note: HA MCP uses 'list_entities' not 'list_devices'
    list_entities_tool = next((t for t in tools if t.name == "list_entities"), None)
    get_state_tool = next((t for t in tools if t.name == "get_state"), None)
    
    if not list_entities_tool or not get_state_tool:
        logger.error(f"❌ Critical HA tools not found! Found: {[t.name for t in tools]}")
        ProcessManager.stop_all()
        return

    logger.info("--- Phase 3: Testing 'list_entities' ---")
    try:
        # list_entities might typically return a list of entity objects
        entities_json = await list_entities_tool.ainvoke({})
        logger.info(f"✅ Entities Found (Raw length: {len(entities_json)})")
        
        # Parse output to find a sensor
        try:
            entities = json.loads(entities_json)
            # Try to find a temperature sensor
            target_entity = None
            for ent in entities:
                entity_id = ent.get("entity_id", "")
                if "temperature" in entity_id or "sensor" in entity_id:
                    target_entity = entity_id
                    break
            
            if not target_entity and entities:
                target_entity = entities[0].get("entity_id")
                
            logger.info(f"🎯 Target Entity for State Check: {target_entity}")
            
        except json.JSONDecodeError:
             logger.warning(f"Could not parse entities JSON: {entities_json[:100]}...")
             target_entity = "sensor.sun_next_dawn" # Fallback guess
             
    except Exception as e:
        logger.error(f"❌ list_entities failed: {e}")
        target_entity = None

    if target_entity:
        logger.info(f"--- Phase 4: Testing 'get_state' on {target_entity} ---")
        try:
            state_info = await get_state_tool.ainvoke({"entity_id": target_entity})
            logger.info(f"✅ State for {target_entity}: {state_info}")
        except Exception as e:
             logger.error(f"❌ get_state failed: {e}")

    logger.info("--- Cleanup ---")
    ProcessManager.stop_all()

if __name__ == "__main__":
    asyncio.run(main())
