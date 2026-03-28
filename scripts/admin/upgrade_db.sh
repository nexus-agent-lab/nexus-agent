#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "/.dockerenv" ]]; then
  echo "Running Alembic upgrade inside container..."
  exec alembic upgrade head
fi

echo "Running Alembic upgrade inside nexus-app container..."
exec docker compose exec -T nexus-app alembic upgrade head
