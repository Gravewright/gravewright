#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.ws-session.yml"
OUT="$ROOT_DIR/tests/performance/ws_live/results_session"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"

# Scenario shape: 3 rooms × 6 players = 18 WS users (2-3 rooms, 15-20 users).
ROOMS=3
USERS_PER_ROOM=6

# Default run length; override with --time <minutes>.
RUN_MINUTES=20

NO_BUILD=false
NO_SEED=false
STATS_PID=""

# Parse args: flags + --time <minutes>.
args=("$@")
i=0
while [[ $i -lt ${#args[@]} ]]; do
  arg="${args[$i]}"
  case "$arg" in
    --no-build) NO_BUILD=true ;;
    --no-seed)  NO_SEED=true ;;
    --time)
      i=$((i + 1))
      RUN_MINUTES="${args[$i]:-$RUN_MINUTES}"
      ;;
    --time=*)
      RUN_MINUTES="${arg#--time=}"
      ;;
  esac
  i=$((i + 1))
done

if ! [[ "$RUN_MINUTES" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "error: --time expects a number of minutes (got '$RUN_MINUTES')" >&2
  exit 2
fi

export RUN_MINUTES

mkdir -p "$OUT"

cleanup() {
  if [[ -n "$STATS_PID" ]]; then
    kill "$STATS_PID" 2>/dev/null || true
  fi
  docker compose -f "$COMPOSE_FILE" down
}
trap cleanup EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Gravewright — LIVE SESSION (multiroom) WebSocket test    ║"
echo "║  18 WS users · 3 rooms × 6 · real tiled maps + tokens    ║"
echo "║  token move · fog · chat/rolls · pan/zoom · reconnect    ║"
printf  "║  run time: %-4s min · app: 1 worker / 2 CPU / 4 GB        ║\n" "$RUN_MINUTES"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ "$NO_SEED" == "false" ]]; then
  echo "[1/6] Seeding $ROOMS rooms × $USERS_PER_ROOM players (accounts + tiled scenes + fog + tokens)..."
  uv run python "$SCRIPT_DIR/performance/ws_live/seed_multiroom.py" \
    --db "$DB_PATH" --rooms "$ROOMS" --users-per-room "$USERS_PER_ROOM"
else
  echo "[1/6] Skipping seed (--no-seed)"
fi

if [[ "$NO_BUILD" == "false" ]]; then
  echo ""
  echo "[2/6] Building Docker image..."
  docker compose -f "$COMPOSE_FILE" build
else
  echo ""
  echo "[2/6] Skipping build (--no-build)"
fi

echo ""
echo "[3/6] Starting app container (1 worker / 2 CPU / 4 GB, fog last-write-wins)..."
docker compose -f "$COMPOSE_FILE" up -d app

echo "      Waiting for health check..."
for i in {1..60}; do
  if docker compose -f "$COMPOSE_FILE" ps app | grep -q "healthy"; then
    echo "      App is healthy."
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    echo "      App did not become healthy after 120s."
    docker compose -f "$COMPOSE_FILE" logs app | tail -50
    exit 1
  fi
  sleep 2
done

APP_CTR="$(docker compose -f "$COMPOSE_FILE" ps -q app)"

echo ""
echo "[4/6] Sampling resource usage → $OUT/docker_stats.txt"
docker stats --no-trunc --format \
  "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
  "$APP_CTR" \
  > "$OUT/docker_stats.txt" 2>&1 &
STATS_PID=$!

echo ""
echo "[5/6] Running live-session driver (18 users / 3 rooms / ${RUN_MINUTES} min)..."
echo "      Live counters stream below."
docker compose -f "$COMPOSE_FILE" run --rm ws_session \
  2>&1 | tee "$OUT/ws_session_output.txt" || true

kill "$STATS_PID" 2>/dev/null || true
STATS_PID=""

echo ""
echo "[6/6] Tearing down..."
docker compose -f "$COMPOSE_FILE" down
trap - EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Done. Results in tests/performance/ws_live/results_session/"
echo "║    summary.md                — human-readable rollup"
echo "║    results_summary.json      — full metrics + latencies"
echo "║    results_timeseries.csv    — per-5s counters over time"
echo "║    docker_stats.txt          — app CPU/RAM samples"
echo "║    ws_session_output.txt     — full console output"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
