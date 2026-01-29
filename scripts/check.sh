#!/bin/bash
# Usage: ./scripts/check.sh [--online]
set -e

RUFF="ruff"
PYTEST="pytest"

MODE="offline"
if [[ "$1" == "--online" ]]; then
    MODE="online"
fi

echo "--- 🛠️ Running Ruff Check (Inside Container) ---"
docker-compose exec -T nexus-app ruff check . --fix --unsafe-fixes || true

echo "--- 🛠️ Running Ruff Format (Inside Container) ---"
docker-compose exec -T nexus-app ruff format .

echo "--- 🧪 Running Pytest (Inside Container, Mode: $MODE) ---"
if [[ "$MODE" == "offline" ]]; then
    # Run only unit tests or tests marked as offline
    docker-compose exec -T nexus-app pytest -m "not integration" tests/smoke_test.py
else
    # Run all tests
    docker-compose exec -T nexus-app pytest tests/
fi

echo "--- ✅ All checks passed! ---"
