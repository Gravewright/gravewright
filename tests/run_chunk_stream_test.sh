#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.chunk-stream.yml"
BASE_OUT="$ROOT_DIR/tests/performance/chunk_stream"
DB_PATH="$ROOT_DIR/storage/gravewright.sqlite3"
RUN_ID="$(date +"%Y%m%d_%H%M%S")"
OUT="$BASE_OUT/runs/$RUN_ID"
LATEST="$BASE_OUT/latest"

NO_BUILD=false
NO_SEED=false
KEEP=false

for arg in "$@"; do
  case "$arg" in
    --no-build) NO_BUILD=true ;;
    --no-seed) NO_SEED=true ;;
    --keep) KEEP=true ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: bash run_chunk_stream_test.sh [--no-build] [--no-seed] [--keep]"
      exit 2
      ;;
  esac
done

mkdir -p "$OUT"

STATS_PID=""
APP_CTR=""
STATUS=1
START_TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
START_SECONDS="$(date +%s)"
GIT_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"

cleanup() {
  echo ""
  echo "[cleanup] Collecting final artifacts..."

  if [[ -n "${APP_CTR:-}" ]]; then
    docker compose -f "$COMPOSE_FILE" ps > "$OUT/compose_ps.txt" 2>&1 || true
    docker compose -f "$COMPOSE_FILE" logs app > "$OUT/app_logs.txt" 2>&1 || true
  fi

  if [[ -n "${STATS_PID:-}" ]]; then
    kill "$STATS_PID" 2>/dev/null || true
    wait "$STATS_PID" 2>/dev/null || true
  fi

  if [[ "$KEEP" == "false" ]]; then
    docker compose -f "$COMPOSE_FILE" down --remove-orphans >/dev/null 2>&1 || true
  else
    echo "[cleanup] Keeping containers because --keep was used."
  fi

  rm -rf "$LATEST"
  mkdir -p "$BASE_OUT"
  cp -R "$OUT" "$LATEST" 2>/dev/null || true

  if command -v zip >/dev/null 2>&1; then
    (
      cd "$OUT"
      zip -qr "chunk_stream_${RUN_ID}.zip" .
    ) || true
  fi
}

trap cleanup EXIT

write_summary() {
  local end_ts
  local end_seconds
  local duration
  local result
  local ok_line
  local scene_line
  local layer_line
  local epoch_line
  local known_line

  end_ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  end_seconds="$(date +%s)"
  duration="$((end_seconds - START_SECONDS))"

  if [[ "$STATUS" -eq 0 ]]; then
    result="PASS"
  else
    result="FAIL"
  fi

  ok_line="$(grep -E "^\[chunk-stream\] OK" "$OUT/chunk_stream_output.txt" 2>/dev/null || true)"
  scene_line="$(grep -E "scene:" "$OUT/chunk_stream_output.txt" 2>/dev/null | tail -n 1 || true)"
  layer_line="$(grep -E "layer:" "$OUT/chunk_stream_output.txt" 2>/dev/null | tail -n 1 || true)"
  epoch_line="$(grep -E "scene_epoch:" "$OUT/chunk_stream_output.txt" 2>/dev/null | tail -n 1 || true)"
  known_line="$(grep -E "known_chunks:" "$OUT/chunk_stream_output.txt" 2>/dev/null | tail -n 1 || true)"

  cat > "$OUT/summary.md" <<EOF

\`\`\`txt
Status:      $result
Started:     $START_TS
Finished:    $end_ts
Duration:    ${duration}s
Git commit:  $GIT_COMMIT
Run ID:      $RUN_ID
\`\`\`

\`\`\`txt
Test:        WebSocket binary viewport + reconnect + session.resume
Compose:     $COMPOSE_FILE
App limit:   1 CPU / 4 GB
Client limit: 0.5 CPU / 512 MB
\`\`\`

\`\`\`txt
${ok_line:-"[chunk-stream] OK not found"}
${scene_line:-"scene:        unknown"}
${layer_line:-"layer:        unknown"}
${epoch_line:-"scene_epoch:  unknown"}
${known_line:-"known_chunks: unknown"}
\`\`\`

\`\`\`txt
[ ] app healthcheck
[ ] login/session discovery
[ ] scene manifest discovery
[ ] viewport.subscribe
[ ] binary chunk frames
[ ] chunk frame header/payload validation
[ ] chunk.ack
[ ] disconnect/reconnect
[ ] session.resume with known_chunks
[ ] clean resume without re-sending known chunks
[ ] scene_epoch mismatch forces resync
\`\`\`

\`\`\`txt
chunk_stream_output.txt
docker_stats.txt
docker_limits.txt
app_logs.txt
compose_ps.txt
summary.md
chunk_stream_${RUN_ID}.zip
\`\`\`
EOF
}

echo ""
echo "============================================================"
echo " gravewright - CHUNK STREAM DOCKER TEST"
echo " WebSocket binary viewport + reconnect + session.resume"
echo " Run ID: $RUN_ID"
echo "============================================================"
echo ""

echo "[0/6] Preparing output directory..."
echo "      $OUT"

if [[ "$NO_SEED" == "false" ]]; then
  echo ""
  echo "[1/6] Seeding chunk-stream scene..."
  uv run python "$BASE_OUT/seed.py" --db "$DB_PATH" \
    2>&1 | tee "$OUT/seed_output.txt"
else
  echo ""
  echo "[1/6] Skipping seed (--no-seed)"
fi

if [[ "$NO_BUILD" == "false" ]]; then
  echo ""
  echo "[2/6] Building Docker image..."
  docker compose -f "$COMPOSE_FILE" build \
    2>&1 | tee "$OUT/build_output.txt"
else
  echo ""
  echo "[2/6] Skipping build (--no-build)"
fi

echo ""
echo "[3/6] Starting app container..."
docker compose -f "$COMPOSE_FILE" up -d app \
  2>&1 | tee "$OUT/compose_up.txt"

echo "      Waiting for health check..."
for i in {1..60}; do
  if docker compose -f "$COMPOSE_FILE" ps app | grep -q "healthy"; then
    echo "      App is healthy."
    break
  fi

  if [[ "$i" -eq 60 ]]; then
    echo "      App did not become healthy after 120s."
    docker compose -f "$COMPOSE_FILE" ps > "$OUT/compose_ps.txt" 2>&1 || true
    docker compose -f "$COMPOSE_FILE" logs app > "$OUT/app_logs.txt" 2>&1 || true
    STATUS=1
    write_summary
    exit "$STATUS"
  fi

  sleep 2
done

APP_CTR="$(docker compose -f "$COMPOSE_FILE" ps -q app)"

echo ""
echo "[4/6] Capturing Docker limits..."
docker inspect "$APP_CTR" \
  --format 'Name={{.Name}} NanoCpus={{.HostConfig.NanoCpus}} Memory={{.HostConfig.Memory}} MemorySwap={{.HostConfig.MemorySwap}}' \
  > "$OUT/docker_limits.txt" 2>&1 || true

cat "$OUT/docker_limits.txt" || true

echo ""
echo "[5/6] Sampling resource usage -> $OUT/docker_stats.txt"
docker stats --no-trunc --format \
  "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" \
  "$APP_CTR" \
  > "$OUT/docker_stats.txt" 2>&1 &
STATS_PID=$!

echo ""
echo "[6/6] Running chunk stream reconnect check..."
set +e
docker compose -f "$COMPOSE_FILE" run --rm chunk_stream \
  2>&1 | tee "$OUT/chunk_stream_output.txt"
STATUS=${PIPESTATUS[0]}
set -e

write_summary

echo ""
echo "============================================================"
if [[ "$STATUS" -eq 0 ]]; then
  echo " PASS — Gate WS-R1 completed successfully."
else
  echo " FAIL — Gate WS-R1 failed."
fi
echo ""
echo " Results:"
echo "   $OUT/"
echo "   $LATEST/"
echo ""
echo " Files:"
echo "   summary.md"
echo "   chunk_stream_output.txt"
echo "   docker_stats.txt"
echo "   docker_limits.txt"
echo "   app_logs.txt"
echo "   compose_ps.txt"
echo "============================================================"
echo ""

exit "$STATUS"
