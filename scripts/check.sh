#!/bin/bash
# Usage: ./scripts/check.sh [--online]
set -e

RUFF="uv run ruff"
PYTEST="uv run pytest"

MODE="offline"
if [[ "$1" == "--online" ]]; then
    MODE="online"
fi

echo "--- 🛠️ Running Ruff Check (Local) ---"
$RUFF check . --fix --unsafe-fixes || true

echo "--- 🛠️ Running Ruff Format (Local) ---"
$RUFF format .

echo "--- 🧪 Running Pytest (Local, Mode: $MODE) ---"
if [[ "$MODE" == "offline" ]]; then
    # Run only unit tests or tests marked as offline
    # Run all non-integration tests
    $PYTEST -m "not integration" tests/
else
    # Run all tests
    $PYTEST tests/
fi

echo "--- ✅ All checks passed! ---"
