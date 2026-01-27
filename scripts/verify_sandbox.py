import asyncio
import os
import sys

# Ensure app is in pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.sandbox import get_sandbox_tool

def test_sandbox():
    print("Initializing Sandbox Tool...")
    try:
        tool = get_sandbox_tool()
    except Exception as e:
        print(f"FAIL: Could not initialize tool. {e}")
        return

    print("Tool initialized. Name:", tool.name)

    # Test 1: Simple Calculation
    code_simple = "print(10 + 20)"
    print(f"\n--- Test 1: Simple Code '{code_simple}' ---")
    try:
        result = tool.run({"code": code_simple})
        print(f"Result: {result}")
        if "30" in result:
            print("PASS")
        else:
            print("FAIL: Expected '30' in output")
    except Exception as e:
        print(f"FAIL: Execution error: {e}")

    # Test 2: Network Isolation Check (should fail)
    code_net = "import urllib.request; print(urllib.request.urlopen('http://www.google.com').status)"
    print(f"\n--- Test 2: Network Isolation '{code_net}' ---")
    try:
        result = tool.run({"code": code_net})
        print(f"Result: {result}")
        if "Execution Error" in result or "Network is unreachable" in result or "Temporary failure in name resolution" in result or "System Error" in result:
            print("PASS: Network request failed as expected.")
        else:
            print("FAIL: Network request seemed to succeed (unexpected).")
    except Exception as e:
        print(f"PASS: Exception caught (likely network error): {e}")

if __name__ == "__main__":
    test_sandbox()
