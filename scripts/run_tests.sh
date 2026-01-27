#!/bin/bash
set -e

echo "--- 🔍 Starting Code Quality Check ---"

# 1. Linting with Ruff
echo "\n[1/2] Running Ruff Linter..."
ruff check app/ scripts/ --select E,F,I --ignore E501

# 2. Testing with Pytest
echo "\n[2/2] Running Pytest Suite..."
# Run pytest, adding current directory to python path
PYTHONPATH=. pytest tests/ -v

echo "\n✅ All Checks Passed!"
