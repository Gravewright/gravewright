# Docker Test Layout

Test-only Docker Compose files live in `tests/`. The root keeps only the production/development application `Dockerfile`.

## Files

```text
Dockerfile
tests/docker-compose.perf.yml
tests/docker-compose.max-stress.yml
tests/docker-compose.i5-stress.yml
tests/docker-compose.chunk-stream.yml
tests/run_perf_test.sh
tests/run_max_stress.sh
tests/run_i5_stress.sh
tests/run_chunk_stream_test.sh
```

## Compose Path Policy

Each test compose file uses:

```yaml
build:
  context: ..
  dockerfile: Dockerfile
```

Volumes are relative to `tests/`:

```yaml
../storage:/app/storage
./performance:/mnt/locust
```

Each file has an explicit Compose project name to avoid stack collisions:

```text
gravewright_perf
gravewright_max_stress
gravewright_i5_stress
gravewright_chunk_stream
```

## Running

Prefer the runner scripts because they seed data, collect stats, and write output paths consistently.

```bash
bash tests/run_perf_test.sh
bash tests/run_chunk_stream_test.sh
```

The scripts resolve paths from their own location, so they can be called from the repository root or another working directory.
