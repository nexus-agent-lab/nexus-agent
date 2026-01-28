import os
import sys

# Ensure app is in pythonpath
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tools.sandbox import get_sandbox_tool


def run_tests():
    tool = get_sandbox_tool()
    print("--- Sandbox Capability Test ---\n")

    # Test 1: Fibonacci
    print("1. Calculating Fibonacci Sequence (First 10):")
    fib_code = """
def fib(n):
    a, b = 0, 1
    result = []
    for _ in range(n):
        result.append(a)
        a, b = b, a + b
    return result

print(f"Fibonacci(10): {fib(10)}")
"""
    try:
        res = tool.run({"code": fib_code})
        print(f"Output:\n{res}")
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: ASCII Art / Sine Wave
    print("\n2. Generating ASCII Sine Wave:")
    art_code = """
import math
print("Sine Wave Plot:")
for i in range(15):
    val = int(10 * math.sin(i * 0.5) + 10)
    print(" " * val + "*")
"""
    try:
        res = tool.run({"code": art_code})
        print(f"Output:\n{res}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    run_tests()
