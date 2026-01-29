import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings

def test_config():
    print("--- Config Verification ---")
    print(f"LLM_MODEL: {settings.LLM_MODEL}")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"FEISHU_APP_ID: {settings.FEISHU_APP_ID}")
    
    assert settings.LLM_API_KEY is not None, "LLM_API_KEY should have default"
    print("✅ Config loaded successfully")

if __name__ == "__main__":
    test_config()
