#!/usr/bin/env bash
set -euo pipefail
SERVICE="${1:-app}"
TIMEOUT="${2:-60}"
END=$((SECONDS + TIMEOUT))
while [ "$SECONDS" -lt "$END" ]; do
  STATUS=$(docker compose ps --format json "$SERVICE" 2>/dev/null | python3 -c "
import sys, json
raw = sys.stdin.read().strip()
if not raw:
    sys.exit(1)
# docker compose may emit one JSON object per line
for line in raw.splitlines():
    o = json.loads(line)
    print(o.get('Health', o.get('Status', '')))
    break
" 2>/dev/null || echo "")
  if echo "$STATUS" | grep -qi healthy; then
    echo "$SERVICE is healthy"
    exit 0
  fi
  sleep 2
done
echo "Timeout waiting for $SERVICE to become healthy" >&2
docker compose ps
exit 1
