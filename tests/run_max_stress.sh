#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.max-stress.yml"
OUT="$ROOT_DIR/tests/performance/max_stress"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"

NO_BUILD=false
NO_SEED=false
for arg in "$@"; do
  [[ "$arg" == "--no-build" ]] && NO_BUILD=true
  [[ "$arg" == "--no-seed"  ]] && NO_SEED=true
done

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Gravewright  —  MAXIMUM STRESS TEST                     ║"
echo "║  500 users  •  8000x6000 map  •  47 000 tiles  •  5 min ║"
echo "║  constraint: 1 CPU / 4 GB RAM (Docker limits)           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

mkdir -p "$OUT"

if [[ "$NO_SEED" == "false" ]]; then
  echo "[1/5] Seeding 47 000-tile stress scene (may take a few minutes)..."
  python "$OUT/seed.py" --db "$DB_PATH"
else
  echo "[1/5] Skipping seed (--no-seed)"
fi

if [[ "$NO_BUILD" == "false" ]]; then
  echo ""
  echo "[2/5] Building Docker image..."
  docker compose -f "$COMPOSE_FILE" build
else
  echo ""
  echo "[2/5] Skipping build (--no-build)"
fi

echo ""
echo "[3/5] Starting app container (1 CPU / 4 GB)..."
docker compose -f "$COMPOSE_FILE" up -d app

echo "      Waiting for health check..."
until docker compose -f "$COMPOSE_FILE" ps app | grep -q "healthy"; do
  sleep 2
done
echo "      App is healthy."

echo ""
echo "[4/5] Sampling resource usage → $OUT/docker_stats.txt"
APP_CTR=$(docker compose -f "$COMPOSE_FILE" ps -q app)
docker stats --no-trunc --format \
  "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
  "$APP_CTR" \
  > "$OUT/docker_stats.txt" 2>&1 &
STATS_PID=$!

echo ""
echo "[5/5] Running Locust — 500 users / spawn 20/s / 300s..."
docker compose -f "$COMPOSE_FILE" run --rm locust \
  2>&1 | tee "$OUT/locust_output.txt" || true

kill $STATS_PID 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" down

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Done. Results in $OUT/"
echo "║    report.html         — visual Locust report"
echo "║    results_stats.csv   — per-endpoint p50/p95/p99"
echo "║    results_history.csv — time-series RPS and latency"
echo "║    docker_stats.txt    — CPU and RAM samples"
echo "║    locust_output.txt   — full console output"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
