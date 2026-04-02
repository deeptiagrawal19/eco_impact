#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

docker compose up -d
sleep 5
cd apps/api
pip install -e .
alembic upgrade head
python seed.py
python fetch_initial_data.py
echo "Setup complete. From repo root run: pnpm dev"
