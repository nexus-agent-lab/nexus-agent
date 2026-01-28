
import sys
import os
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.skill_loader import SkillLoader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_skill_registry")

def main():
    logger.info("Testing SkillLoader.load_registry()...")
    
    registry_text = SkillLoader.load_registry()
    
    print("\n--- REGISTRY OUTPUT START ---\n")
    print(registry_text)
    print("\n--- REGISTRY OUTPUT END ---\n")
    
    if "Blindness Rule" in registry_text:
        logger.info("✅ SUCCESS: Found 'Blindness Rule' in registry.")
    else:
        logger.error("❌ FAILURE: 'Blindness Rule' MISSING from registry.")
        
    if "Examples" in registry_text:
        logger.error("❌ FAILURE: Found 'Examples' in registry (should be excluded).")
    else:
        logger.info("✅ SUCCESS: 'Examples' correctly excluded.")

if __name__ == "__main__":
    main()
