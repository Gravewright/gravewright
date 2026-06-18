#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.perf.yml"
OUT="$ROOT_DIR/tests/performance"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"

NO_BUILD=false
STATS_PID=""

cleanup() {
  if [[ -n "$STATS_PID" ]]; then
    kill "$STATS_PID" 2>/dev/null || true
  fi
  docker compose -f "$COMPOSE_FILE" down
}

trap cleanup EXIT

for arg in "$@"; do
  [[ "$arg" == "--no-build" ]] && NO_BUILD=true
done

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Gravewright performance test"
echo "  constraint: 1 CPU / 4 GB RAM (Docker limits)"
echo "═══════════════════════════════════════════════════"
echo ""

echo "[1/5] Seeding test data..."
uv run python "$OUT/seed.py" --db "$DB_PATH"

if [[ "$NO_BUILD" == "false" ]]; then
  echo ""
  echo "[2/5] Building Docker image..."
  docker compose -f "$COMPOSE_FILE" build
else
  echo ""
  echo "[2/5] Skipping build (--no-build)"
fi

echo ""
echo "[3/5] Starting constrained app container (1 CPU / 4 GB)..."
docker compose -f "$COMPOSE_FILE" up -d app

echo "      Waiting for app to be healthy..."
until docker compose -f "$COMPOSE_FILE" ps app | grep -q "healthy"; do
  sleep 2
done
echo "      App is healthy."

echo ""
echo "[4/5] Collecting resource usage (docker stats → tests/performance/docker_stats.txt)..."
docker stats --no-trunc --format \
  "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" \
  "$(docker compose -f "$COMPOSE_FILE" ps -q app)" \
  > "$OUT/docker_stats.txt" 2>&1 &
STATS_PID=$!

echo ""
echo "[5/5] Running Locust (20 users, 90s, headless)..."
docker compose -f "$COMPOSE_FILE" run --rm locust \
  2>&1 | tee "$OUT/locust_output.txt"

kill $STATS_PID 2>/dev/null || true
STATS_PID=""
docker compose -f "$COMPOSE_FILE" down
trap - EXIT

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Done. Results in tests/performance/"
echo "    report.html          — visual Locust report"
echo "    results_stats.csv    — per-endpoint stats"
echo "    results_history.csv  — time-series RPS/latency"
echo "    docker_stats.txt     — CPU/RAM samples"
echo "    locust_output.txt    — full console output"
echo "═══════════════════════════════════════════════════"
echo ""
