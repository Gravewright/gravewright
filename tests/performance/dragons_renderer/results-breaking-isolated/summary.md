# Historical renderer baseline — headed, isolated browsers

This run predates the fast-sprite/shared-instance optimization used by Beta 1.
Its 1,250–3,000 degradation points are retained as the comparison baseline and
must not be described as the optimized renderer's current knee. The optimized
callback-budget knee is documented in
[`../results-fast-sprites-knee-final/summary.md`](../results-fast-sprites-knee-final/summary.md).

Each count ran in a fresh visible Chromium process with one shared animated texture, 10 s warm-up and 30 s measurement. Background, renderer and occluded-window throttling were disabled.

| Visible | Frame p50 | Frame p95 | Frame p99 | Callback p95 | App render p95 |
|---:|---:|---:|---:|---:|---:|
| 1000 | 16.7 ms | 17.0 ms | 17.1 ms | 12.1 ms | 8.5 ms |
| 1250 | 16.7 ms | 16.9 ms | 17.4 ms | 12.1 ms | 8.9 ms |
| 1500 | 16.7 ms | 33.4 ms | 33.5 ms | 19.7 ms | 16.5 ms |
| 1750 | 16.7 ms | 33.4 ms | 33.6 ms | 26.1 ms | 22.6 ms |
| 2000 | 32.8 ms | 33.5 ms | 33.7 ms | 29.5 ms | 25.6 ms |
| 2500 | 33.5 ms | 1016.7 ms | 1016.8 ms | 40.4 ms | 32.5 ms |
| 3000 | 1016.5 ms | 1016.8 ms | 1016.8 ms | 50.5 ms | 35.2 ms |

The first reproducible degradation is 1500 visible instances, where p95 drops from 60 Hz to 30 Hz. At 2000 visible instances the median also settles at 30 Hz. At 2500 the browser enters an unstable approximately-1-Hz presentation regime in the tail; at 3000 that catastrophic regime dominates the entire run.

The renderer's practical 60-Hz capacity on this machine is therefore between 1250 and 1500 simultaneously visible animated tokens. The practical stable 30-Hz ceiling is approximately 2000. Texture memory remains one 0.0625 MiB shared source throughout; the collapse is per-instance render work, not asset duplication.
