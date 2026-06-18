#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.i5-stress.yml"
OUT="$ROOT_DIR/tests/performance/i5_stress"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"

NO_BUILD=false
NO_SEED=false
for arg in "$@"; do
  [[ "$arg" == "--no-build" ]] && NO_BUILD=true
  [[ "$arg" == "--no-seed"  ]] && NO_SEED=true
done

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Gravewright  —  STRESS TEST  (i5-8400 / 8 GB)          ║"
echo "║  6 cores  •  8 GB RAM  •  1 worker   •  500 usuários    ║"
echo "║  mapa 8000×6000  •  47 000 tiles  •  5 minutos          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ "$NO_SEED" == "false" ]]; then
  echo "[1/5] Seeding 47 000-tile stress scene..."
  uv run python "$OUT/seed.py" --db "$DB_PATH"
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
echo "[3/5] Starting app container (6 CPUs / 8 GB / 1 worker)..."
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
echo "║  Done. Resultados em $OUT/"
echo "║    report.html         — relatório visual Locust"
echo "║    results_stats.csv   — p50/p95/p99 por endpoint"
echo "║    results_history.csv — RPS e latência por tempo"
echo "║    docker_stats.txt    — amostras de CPU e RAM"
echo "║    locust_output.txt   — saída completa do console"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
