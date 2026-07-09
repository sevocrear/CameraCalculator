#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose build app test
docker compose up -d app
chmod +x scripts/wait_healthy.sh
./scripts/wait_healthy.sh app 60
docker compose --profile test run --rm test
docker compose down
