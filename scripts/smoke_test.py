import sys
import os

# Set path so we can import app
sys.path.append(os.getcwd())

print("--- 🔍 Running Smoke Test ---")

try:
    print("Checking app.core.agent...")
    import app.core.agent
    print("✅ app.core.agent imported")

    print("Checking app.interfaces.telegram...")
    import app.interfaces.telegram
    print("✅ app.interfaces.telegram imported")

    print("Checking app.main...")
    import app.main
    print("✅ app.main imported")

    print("--- ✨ Smoke Test Passed ---")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ SMOEK TEST FAILED: {e}")
    sys.exit(1)
