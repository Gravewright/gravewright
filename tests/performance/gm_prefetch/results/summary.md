# Andromeda — GM-guided predictive streaming

## Scenario

- Image: 40,000 × 12,788 px (511.52 MP), 304,276,710 bytes.
- Raster: 1,975 tiles of 512 × 512 px.
- Clients: 1 GM and 5 independent Chromium player contexts.
- Baseline: cold reveal of an unvisited adjacent chunk.
- Guided: GM visits/dwells before the same reveal; player caches start cold.
- Completion: four or more target tile sprites presented per player.

## A/B result

| Metric | Baseline | GM-guided | Change |
|---|---:|---:|---:|
| Reveal p50 | 954.4 ms | 400.7 ms | **−58.02%** |
| Reveal p95 | 1,129.6 ms | 466.3 ms | **−58.72%** |
| Requests during reveal | 71 | 1 | **−98.59%** |
| Promotion rate | — | 5/5 (100%) | — |
| Useful byte ratio | — | 22.1–22.7% | — |
| Scheduler debt after reveal | — | 0 ms | — |

Player reveal times:

- Baseline: 743.0, 938.4, 954.4, 1,151.0, 1,129.6 ms.
- GM-guided: 466.3, 526.1, 239.6, 299.4, 400.7 ms.

Each promotion cancelled the remaining speculative fetch (`gm_hint_cancelled=1`),
left no scheduler debt, and avoided approximately 275–402 ms of measured network
latency for visible tiles. The low useful-byte ratio is now visible and provides
a concrete target for subsequent policy calibration.
