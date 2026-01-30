
import asyncio
import os
import sys
from unittest.mock import MagicMock

# Ensure we can import app
sys.path.append(os.getcwd())

from app.core.skill_loader import SkillLoader
from app.core.agent import create_agent_graph
from app.models.user import User

async def test_role_filtering():
    print("--- Testing Role-Based Skill Filtering ---")

    # 1. Test SkillLoader direct filtering
    print("\n1. Testing SkillLoader.load_summaries() output...")
    admin_summary = SkillLoader.load_summaries(role="admin")
    user_summary = SkillLoader.load_summaries(role="user")
    
    if "System Management" in admin_summary:
        print("✅ Admin summary includes System Management.")
    else:
        print("❌ Admin summary MISSING System Management.")
        
    if "System Management" not in user_summary:
        print("✅ User summary EXCLUDES System Management.")
    else:
        print("❌ User summary WRONGLY INCLUDES System Management.")

    # 2. Test Agent Node Logic (Partial verify via rules)
    print("\n2. Testing SkillLoader.load_registry_with_metadata()...")
    admin_registry = SkillLoader.load_registry_with_metadata(role="admin")
    user_registry = SkillLoader.load_registry_with_metadata(role="user")
    
    admin_skill_names = [s["name"] for s in admin_registry]
    user_skill_names = [s["name"] for s in user_registry]
    
    print(f"Admin Skills: {admin_skill_names}")
    print(f"User Skills: {user_skill_names}")
    
    if "system_management" in admin_skill_names and "system_management" not in user_skill_names:
        print("✅ Registry filtering works.")
    else:
        print("❌ Registry filtering failed.")

    print("\n--- Role Filtering Test Completed ---")

if __name__ == "__main__":
    asyncio.run(test_role_filtering())
