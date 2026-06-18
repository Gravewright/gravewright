#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.ws-live.yml"
OUT="$ROOT_DIR/tests/performance/ws_live/results"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"

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
echo "║  Gravewright — LIVE SESSION WebSocket test               ║"
echo "║  15 WS users · token move · fog ops · chat/rolls         ║"
echo "║  reconnect/resume · 20 minutes · 1 CPU / 4 GB app        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ "$NO_SEED" == "false" ]]; then
  echo "[1/6] Seeding live scene (tokens + fog + chunks)..."
  uv run python "$SCRIPT_DIR/performance/ws_live/seed.py" --db "$DB_PATH"
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
echo "[3/6] Starting app container (1 CPU / 4 GB, fog last-write-wins)..."
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
echo "[5/6] Running live-session driver (15 users / 1200s)..."
echo "      This takes ~20 minutes. Live counters stream below."
docker compose -f "$COMPOSE_FILE" run --rm ws_live \
  2>&1 | tee "$OUT/ws_live_output.txt" || true

kill "$STATS_PID" 2>/dev/null || true
STATS_PID=""

echo ""
echo "[6/6] Tearing down..."
docker compose -f "$COMPOSE_FILE" down
trap - EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Done. Results in tests/performance/ws_live/results/"
echo "║    summary.md                — human-readable rollup"
echo "║    results_summary.json      — full metrics + latencies"
echo "║    results_timeseries.csv    — per-5s counters over time"
echo "║    docker_stats.txt          — app CPU/RAM samples"
echo "║    ws_live_output.txt        — full console output"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
