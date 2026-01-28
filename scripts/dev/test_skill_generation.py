#!/usr/bin/env python3
"""
Test script for skill card generation.

This script tests the SkillGenerator by generating a skill card
for Home Assistant using the actual MCP tool definitions.

Usage:
    uv run python scripts/dev/test_skill_generation.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up environment for skill generation LLM
# Use local LLM by default, can be overridden
os.environ.setdefault("SKILL_GEN_PROVIDER", "local")
os.environ.setdefault("LLM_API_KEY", os.getenv("LLM_API_KEY", ""))
os.environ.setdefault("LLM_BASE_URL", os.getenv("LLM_BASE_URL", ""))
os.environ.setdefault("LLM_MODEL", os.getenv("LLM_MODEL", ""))


# Sample Home Assistant MCP tool definitions (based on actual schema)
HOMEASSISTANT_TOOLS = [
    {
        "name": "query_entities",
        "description": ("Search and filter Home Assistant entities. Returns matching entities with current states."),
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Entity domain filter (e.g., 'light', 'switch', 'climate', 'sensor')",
                },
                "query": {
                    "type": "string",
                    "description": "Search query to filter entities by name or ID (supports Chinese)",
                },
                "area": {"type": "string", "description": "Filter by area/room name"},
            },
        },
    },
    {
        "name": "get_entity_state",
        "description": "Get the current state and attributes of a specific entity.",
        "parameters": {
            "type": "object",
            "properties": {"entity_id": {"type": "string", "description": "The entity ID (e.g., 'light.living_room')"}},
            "required": ["entity_id"],
        },
    },
    {
        "name": "call_service",
        "description": (
            "Call a Home Assistant service to control an entity. Use to turn on/off devices, set temperature, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "domain": {"type": "string", "description": "Service domain (e.g., 'light', 'switch', 'climate')"},
                "service": {
                    "type": "string",
                    "description": "Service name (e.g., 'turn_on', 'turn_off', 'set_temperature')",
                },
                "entity_id": {"type": "string", "description": "Target entity ID"},
                "service_data": {
                    "type": "object",
                    "description": "Additional service data (e.g., brightness, temperature)",
                },
            },
            "required": ["domain", "service", "entity_id"],
        },
    },
    {
        "name": "get_history",
        "description": "Get historical state changes for an entity over a time period.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "The entity ID to get history for"},
                "start_time": {"type": "string", "description": "Start time in ISO format"},
                "end_time": {"type": "string", "description": "End time in ISO format"},
            },
            "required": ["entity_id"],
        },
    },
]


async def test_skill_generation():
    """Test skill card generation."""
    from app.core.skill_generator import SkillGenerator
    from app.core.skill_loader import SkillLoader

    print("=" * 60)
    print("Testing Skill Card Generation")
    print("=" * 60)

    # Show current LLM config
    provider = os.getenv("SKILL_GEN_PROVIDER", "local")
    print(f"\nUsing LLM Provider: {provider}")
    if provider == "local":
        print(f"  Model: {os.getenv('LLM_MODEL', 'not set')}")
        print(f"  Base URL: {os.getenv('LLM_BASE_URL', 'not set')}")

    print("\nGenerating skill card for 'homeassistant'...")
    print(f"Tool count: {len(HOMEASSISTANT_TOOLS)}")
    print("Tools:", [t["name"] for t in HOMEASSISTANT_TOOLS])

    try:
        # Generate skill card
        skill_content = await SkillGenerator.generate_skill_card(
            mcp_name="homeassistant", tools=HOMEASSISTANT_TOOLS, domain="smart_home"
        )

        print("\n" + "=" * 60)
        print("Generated Skill Card:")
        print("=" * 60)
        print(skill_content)

        # Ask user if they want to save
        print("\n" + "=" * 60)
        save = input("Save to skills/homeassistant.md? [y/N]: ").strip().lower()

        if save == "y":
            success = SkillLoader.save_skill("homeassistant", skill_content)
            if success:
                print("✅ Saved successfully!")
            else:
                print("❌ Failed to save")
        else:
            print("Not saved.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_skill_generation())
