#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if ! python3 -c "import coverage" >/dev/null 2>&1; then
    echo "coverage is required. Install it with 'pip install coverage' before committing." >&2
    exit 1
fi

# Add backend to PYTHONPATH so internal imports work
export PYTHONPATH="$REPO_ROOT/backend:${PYTHONPATH:-}"

python3 -m coverage erase
python3 -m coverage run --source=backend --omit='*/tests/*,backend/socket_server.py,backend/event_handlers.py,backend/managers/village_generator.py,backend/managers/village_generator_backup.py' -m unittest discover -s backend -p 'test_*.py'
python3 -m coverage report --fail-under=80 --sort=cover
