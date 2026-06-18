#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.browser-bench.yml"
OUT="$ROOT_DIR/tests/performance/browser_bench/results"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"
HOST="http://localhost:8007"

# Defaults; override on the command line.
RUN_MINUTES=3
CPU_THROTTLE=1
GPU=on
HEADED=""
NO_BUILD=false
NO_SEED=false
STATS_PID=""

# Pass-through args: --time <min>, --cpu-throttle <n>, --gpu on|off, --headed,
# --no-build, --no-seed.
args=("$@")
i=0
while [[ $i -lt ${#args[@]} ]]; do
  arg="${args[$i]}"
  case "$arg" in
    --no-build) NO_BUILD=true ;;
    --no-seed)  NO_SEED=true ;;
    --headed)   HEADED="--headed" ;;
    --time)         i=$((i + 1)); RUN_MINUTES="${args[$i]:-$RUN_MINUTES}" ;;
    --time=*)       RUN_MINUTES="${arg#--time=}" ;;
    --cpu-throttle) i=$((i + 1)); CPU_THROTTLE="${args[$i]:-$CPU_THROTTLE}" ;;
    --cpu-throttle=*) CPU_THROTTLE="${arg#--cpu-throttle=}" ;;
    --gpu)          i=$((i + 1)); GPU="${args[$i]:-$GPU}" ;;
    --gpu=*)        GPU="${arg#--gpu=}" ;;
  esac
  i=$((i + 1))
done

mkdir -p "$OUT"

cleanup() {
  if [[ -n "$STATS_PID" ]]; then kill "$STATS_PID" 2>/dev/null || true; fi
  docker compose -f "$COMPOSE_FILE" down
}
trap cleanup EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Gravewright — REAL-BROWSER benchmark (Playwright)        ║"
echo "║  time-to-map · FPS/stutter on pan+zoom · browser memory  ║"
printf  "║  run: %-3s min · cpu_throttle: %-2sx · gpu: %-3s · headed:%-2s ║\n" \
  "$RUN_MINUTES" "$CPU_THROTTLE" "$GPU" "$([[ -n "$HEADED" ]] && echo y || echo n)"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ "$NO_SEED" == "false" ]]; then
  echo "[1/5] Seeding live scene (real tiled map + tokens + fog)..."
  uv run python "$SCRIPT_DIR/performance/ws_live/seed.py" --db "$DB_PATH"
else
  echo "[1/5] Skipping seed (--no-seed)"
fi

echo ""
echo "[2/5] Ensuring Playwright Chromium is installed..."
uv run --with playwright python -m playwright install chromium

if [[ "$NO_BUILD" == "false" ]]; then
  echo ""
  echo "[3/5] Building + starting app container (2 CPU / 2 GB)..."
  docker compose -f "$COMPOSE_FILE" up -d --build app
else
  echo ""
  echo "[3/5] Starting app container (--no-build)..."
  docker compose -f "$COMPOSE_FILE" up -d app
fi

echo "      Waiting for health check..."
for n in {1..60}; do
  if docker compose -f "$COMPOSE_FILE" ps app | grep -q "healthy"; then
    echo "      App is healthy."
    break
  fi
  if [[ "$n" -eq 60 ]]; then
    echo "      App did not become healthy after 120s."
    docker compose -f "$COMPOSE_FILE" logs app | tail -50
    exit 1
  fi
  sleep 2
done

echo ""
echo "[4/5] Running browser benchmark (${RUN_MINUTES} min of pan/zoom)..."
uv run --with playwright --with psutil python \
  "$SCRIPT_DIR/performance/browser_bench/browser_bench.py" \
  --host "$HOST" \
  --time "$RUN_MINUTES" \
  --cpu-throttle "$CPU_THROTTLE" \
  --gpu "$GPU" \
  $HEADED \
  --output "$OUT" \
  2>&1 | tee "$OUT/browser_bench_output.txt" || true

echo ""
echo "[5/5] Tearing down..."
docker compose -f "$COMPOSE_FILE" down
trap - EXIT

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Done. Results in tests/performance/browser_bench/results/"
echo "║    summary.md                — human-readable rollup"
echo "║    results_summary.json      — milestones + fps + memory"
echo "║    samples.csv               — per-second heap/RSS"
echo "║    final_frame.png           — last rendered frame"
echo "║    browser_bench_output.txt  — console output"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
