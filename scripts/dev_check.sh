#!/bin/bash
set -e

# Nexus Agent Development Check Script
# Usage: ./scripts/dev_check.sh

echo "========================================"
echo "🚀 Nexus Agent: Quick Health Check"
echo "========================================"

# 1. Syntax & Style Check (Ruff)
echo -e "\n🔍 [1/2] Running Static Analysis (Ruff)..."
if command -v uv &> /dev/null; then
    echo "   Using local 'uv'..."
    if [ -f "requirements-dev.txt" ]; then
        echo "   Installing dev dependencies..."
        uv pip install -r requirements-dev.txt -q
    fi
    uv run ruff check app tests --fix
elif command -v ruff &> /dev/null; then
    echo "   Using local ruff..."
    ruff check app tests --fix
else
    echo "   ⚠️ Local 'ruff' not found. Installing in container temporary or skipping..."
    # Fallback to docker if available
    if docker-compose ps | grep "nexus-app" &> /dev/null; then
        echo "   Using Docker ruff..."
        # Install ruff if missing in container (it's fast)
        docker-compose exec -T nexus-app pip install ruff -q
        docker-compose exec -T nexus-app ruff check . --select E,F,W,I --ignore E501
    else
        echo "   ❌ Docker not running and local ruff missing. Skipping linting."
    fi
fi

# 2. Logic Tests (Pytest in Docker)
echo -e "\n🧪 [2/2] Running Unit Tests (Docker)..."
if docker-compose ps | grep "nexus-app" &> /dev/null; then
    echo "   Running tests in 'nexus-app' container..."
    # Ensure test dependencies are installed (ephemeral)
    docker-compose exec -T nexus-app pip install pytest pytest-asyncio pytest-mock httpx -q
    
    # Only run unit tests for speed, skip slow integration tests
    docker-compose exec -T nexus-app env PYTHONPATH=/app pytest tests/ -v
else
    echo "   ❌ Nexus App container is NOT running."
    echo "   Please start it with: docker-compose up -d"
    exit 1
fi

echo -e "\n✅ Check Complete! Ready to push."
