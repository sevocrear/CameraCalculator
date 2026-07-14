#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cleanup() {
    local status=$?
    trap - EXIT INT TERM
    docker compose --profile test down --remove-orphans || true
    exit "$status"
}
trap cleanup EXIT INT TERM

docker compose build app test
docker compose up -d app
bash scripts/wait_healthy.sh app 60
docker compose --profile test run --rm test
