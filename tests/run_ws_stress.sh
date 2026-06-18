#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.ws-stress.yml"
OUT="$ROOT_DIR/tests/performance/ws_live/results_stress"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"
ROOMS=100
USERS_PER_ROOM=5

NO_BUILD=false
NO_SEED=false
STATS_PID=""

for arg in "$@"; do
  [[ "$arg" == "--no-build" ]] && NO_BUILD=true
  [[ "$arg" == "--no-seed"  ]] && NO_SEED=true
done

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
echo "║  Gravewright — WebSocket STRESS TEST (sharded rooms)     ║"
echo "║  500 WS users · 100 rooms × 5 · distinct accounts        ║"
echo "║  token move · fog ops · chat/rolls · reconnect/resume    ║"
echo "║  20 minutes · app: 1 worker · 6 CPU / 8 GB               ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ "$NO_SEED" == "false" ]]; then
  echo "[1/6] Seeding $ROOMS rooms × $USERS_PER_ROOM players (accounts + scenes + fog + tokens)..."
  echo "      (creates up to $((ROOMS * USERS_PER_ROOM)) accounts; first run takes a minute)"
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
echo "[3/6] Starting app container (1 worker / 6 CPU / 8 GB)..."
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
echo "[5/6] Running stress driver (500 users / spawn 20/s / 1200s)..."
echo "      ~25s ramp, then ~20 minutes of load. Counters stream below."
docker compose -f "$COMPOSE_FILE" run --rm ws_stress \
  2>&1 | tee "$OUT/ws_stress_output.txt" || true

kill "$STATS_PID" 2>/dev/null || true
STATS_PID=""

echo ""
echo "[6/6] Tearing down..."
docker compose -f "$COMPOSE_FILE" down
trap - EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Done. Results in tests/performance/ws_live/results_stress/"
echo "║    summary.md                — human-readable rollup"
echo "║    results_summary.json      — full metrics + latencies"
echo "║    results_timeseries.csv    — per-5s counters over time"
echo "║    docker_stats.txt          — app CPU/RAM samples"
echo "║    ws_stress_output.txt      — full console output"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
