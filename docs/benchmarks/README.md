# Benchmark reports

These reports preserve benchmark conclusions suitable for project documentation. Executable harnesses and machine-readable artifacts live under `tests/performance/`.

- [RTX 4060 realistic-scene result](gravewright-realistic-rtx4060.md)
- [Methodology and interpretation](../performance.md)
- [Synthetic dragon report](../../tests/performance/dragons_renderer/results-gpu-rtx4060/summary.md)

## Simulating a low-end PC

Seed the dedicated benchmark campaign and start the performance server:

```bash
uv run python tests/performance/ws_live/seed.py --tokens 300
ALLOWED_HOSTS=localhost,localhost:8007,127.0.0.1,127.0.0.1:8007 \
  grave run --host 127.0.0.1 --port 8007
```

Then run the browser matrix in another terminal:

```bash
uv run --with playwright --with psutil python \
  tests/performance/browser_bench/low_end_bench.py \
  --host http://localhost:8007
```

The default matrix compares Low, Medium, and High graphics at 1×, 4×, and 6×
CPU slowdown for 30 seconds each. It normally completes in under ten minutes
after the map is seeded. Results are written to
`tests/performance/browser_bench/results-low-end/summary.md` and `matrix.json`.

For a quick smoke run:

```bash
uv run --with playwright --with psutil python \
  tests/performance/browser_bench/low_end_bench.py \
  --profiles low --throttles 4 --duration 5
```

Only the Low/4× baseline is a release gate. Software rendering (`--gpu off`) is
kept diagnostic because it is substantially slower than a typical integrated
GPU and would make the acceptance limits misleading.

Historical or invalid attempts are not silently converted into medians. Each report states how many runs passed its validity gates.
