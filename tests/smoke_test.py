import os
import sys

import pytest

# Set path so we can import app
sys.path.append(os.getcwd())


def test_imports():
    """Smoke test to ensure core components can be imported."""
    print("--- 🔍 Running Smoke Test ---")

    # We use importlib to check if components can be imported
    import importlib

    components = ["app.core.agent", "app.interfaces.telegram", "app.main"]

    for component in components:
        try:
            importlib.import_module(component)
            print(f"✅ {component} imported")
        except Exception as e:
            pytest.fail(f"❌ Failed to import {component}: {e}")

    print("--- ✨ Smoke Test Passed ---")


if __name__ == "__main__":
    # If run directly, we call the test manually
    try:
        test_imports()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ SMOKE TEST FAILED: {e}")
        sys.exit(1)
