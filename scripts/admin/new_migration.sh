#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/admin/new_migration.sh \"migration message\""
  exit 1
fi

MESSAGE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ -f "/.dockerenv" ]]; then
  echo "Creating Alembic revision inside container..."
  exec alembic revision --autogenerate -m "$MESSAGE"
fi

echo "Creating Alembic revision inside nexus-app container..."
exec docker compose exec -T nexus-app alembic revision --autogenerate -m "$MESSAGE"
