#!/bin/bash
set -euo pipefail  # Fail-fast: exit on error, unset vars, or pipe failure

# Nexus Agent Development Check Script
# Usage: ./scripts/dev_check.sh

echo "========================================"
echo "🚀 Nexus Agent: Quality Assurance Check"
echo "========================================"

# 1. Python Syntax Verification (Strict CPython Parser)
echo -e "\n🐍 [1/4] Verifying Python Syntax (py_compile)..."
error_found=0
while IFS= read -r -d '' pyfile; do
    if ! python3 -m py_compile "$pyfile" > /dev/null 2>&1; then
        echo "   ❌ Syntax Error in: $pyfile"
        python3 -m py_compile "$pyfile" || true # Show the error
        error_found=1
    fi
done < <(find app tests scripts -name "*.py" -print0 2>/dev/null)

if [ "$error_found" -ne 0 ]; then
    echo -e "\n🛑 FATAL: Syntax errors detected. Fix them before continuing."
    exit 1
fi
echo "   ✅ All Python files parse correctly."

# 2. Static Analysis (Ruff)
echo -e "\n🔍 [2/4] Running Static Analysis (Ruff)..."
if ! command -v uv &> /dev/null; then
    echo "   ❌ 'uv' not found. Please install uv first."
    exit 1
fi

uv run ruff check app/ tests/ scripts/ --select E,F,I --ignore E501
echo "   ✅ Ruff passed."

# 3. Frontend Verification (Conditional Docker Build)
# This will trigger 'npm run build' inside the container
echo -e "\n🌐 [3/4] Checking Frontend Changes..."
if ! git diff --quiet HEAD -- web/ || [ ! -d "web/.next" ]; then
    echo "   Detected changes in 'web/' or missing build artifacts. Running 'docker-compose build web'..."
    if ! docker-compose build web; then
        echo -e "\n🛑 FATAL: Frontend build failed. Fix the issues in 'web/' before continuing."
        exit 1
    fi
    echo "   ✅ Frontend build successful."
else
    echo "   ✅ No web changes detected, skipping build."
fi

# 4. Logic & Integration Tests (Pytest)
echo -e "\n🧪 [4/4] Running Unit Tests (Local uv)..."
PYTHONPATH=. uv run pytest tests/ -v --tb=short

echo -e "\n✅ Check Complete! All systems go."
