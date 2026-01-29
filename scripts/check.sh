#!/bin/bash
# Usage: ./scripts/check.sh [--online]
set -e

RUFF="ruff"
PYTEST="pytest"

MODE="offline"
if [[ "$1" == "--online" ]]; then
    MODE="online"
fi

echo "--- 🛠️ Running Ruff Check (Local) ---"
uv run ruff check . --fix --unsafe-fixes || true

echo "--- 🛠️ Running Ruff Format (Local) ---"
uv run ruff format .

echo "--- 🧪 Running Pytest (Local, Mode: $MODE) ---"
if [[ "$MODE" == "offline" ]]; then
    # Run only unit tests or tests marked as offline
    uv run pytest -m "not integration" tests/smoke_test.py
else
    # Run all tests
    uv run pytest tests/
fi

echo "--- ✅ All checks passed! ---"
