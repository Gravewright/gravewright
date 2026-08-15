# Gravewright 100 Dragons

## Environment

- Windows 11, Chromium 151.0.7922.34, headless
- Viewport 1366×768, DPR 1
- Workload: animated 128×128 canvas texture, continuously updated
- Important limitation: this measures shared animated texture/render cost, not WebM decode cost

## Canonical — 100 visible, 1 unique asset

Five runs, each with 10 s warm-up and 30 s measurement.

- Frame p50 median: 33.40 ms
- Frame p95 median: 50.10 ms
- Frame p99 median: 50.10 ms
- App render p95 median: 4.20 ms
- JS heap median: 52.14 MiB
- Chromium process-tree RSS median: 807.71 MiB
- Logical GPU bytes: 0.0625 MiB
- Texture sources: 1
- Shared asset hits: 99

The renderer does share the heavy texture, but the end-to-end frame cadence misses both the 60 Hz and 30 Hz p95 budgets in this headless workload.

### Where are the other ~46 ms?

A focused 30 s diagnostic run decomposed the canonical frame:

| Phase | p95 |
|---|---:|
| Animated canvas update | 0.10 ms |
| Render preparation | 1.40 ms |
| Synchronous `app.render()` submission | 3.60 ms |
| Entire animation callback / redraw | 5.20 ms |
| Frame interval | 50.00 ms |
| Unattributed scheduling/compositor gap | 44.80 ms |

Only two 51 ms browser long tasks occurred in the whole measurement, so ordinary main-thread long tasks do not explain the steady 50 ms cadence. The missing time is between animation callbacks: compositor/GPU backpressure and missed vsync slots in headless Chromium. `app.render()` measures synchronous command submission, not completion/presentation of GPU work.

This means `frame p95 - app_render p95` must not be labelled as unexplained CPU time. The benchmark now records `animation_callback_ms_p95`, `unattributed_frame_gap_ms_p95`, long-task count and long-task p95 explicitly.

### Headless vs headed, identical 100/100/1 workload

Both runs used 10 s warm-up and 30 s measurement on the same machine.

| Metric | Headless | Headed |
|---|---:|---:|
| Callback p95 | 5.20 ms | 8.80 ms |
| App render p95 | 3.60 ms | 5.20 ms |
| Frame p95 | 50.00 ms | 16.80 ms |
| Unattributed gap p95 | 44.80 ms | 8.00 ms |
| Frame p99 | 50.10 ms | 16.90 ms |
| Frames in 30 s | 812 | 1800 |
| Long tasks | 2 | 0 |

The visible Chromium run holds approximately 60 Hz. Its synchronous callback is actually 3.6 ms more expensive, yet presentation is dramatically better. This confirms that the 50 ms headless result was dominated by headless compositor/rAF scheduling behavior, not hidden Gravewright CPU work. Headless frame cadence must therefore not be used as the renderer acceptance metric; internal CPU timings remain useful there, while frame pacing should be measured headed.

### Headed scale run — 250 / 500 / 750 / 1000

Each point used the identical shared animated source, 10 s warm-up and 30 s measurement.

| Requested | Actually visible | Callback p95 | App render p95 | Frame p95 | Gap p95 |
|---:|---:|---:|---:|---:|---:|
| 250 | 250 | 7.7 ms | 4.0 ms | 16.9 ms | 9.2 ms |
| 500 | 500 | 12.3 ms | 8.7 ms | 16.9 ms | 4.6 ms |
| 750 | 710 | 17.1 ms | 12.2 ms | 16.9 ms | 0.0 ms |
| 1000 | 805 | 19.6 ms | 14.6 ms | 33.3 ms | 13.7 ms |

The 60 Hz operating range extends through 500 fully visible instances. At 750 requested instances the callback reaches the 16.67 ms budget and culling admits 710. At 1000 requested / 805 visible, synchronous work exceeds the budget and frame p95 moves to the 30 Hz band. The shared texture remains one 0.0625 MiB logical GPU source at every point.

## Visible-instance ladder

| Requested | Actually visible | Frame p95 | App render p95 |
|---:|---:|---:|---:|
| 1 | 1 | 16.7 ms | 0.4 ms |
| 10 | 10 | 16.8 ms | 1.2 ms |
| 25 | 25 | 16.8 ms | 1.9 ms |
| 50 | 50 | 33.4 ms | 2.7 ms |
| 100 | 100 | 50.0 ms | 4.1 ms |
| 150 | 150 | 66.7 ms | 5.6 ms |
| 250 | 250 | 100.0 ms | 8.0 ms |
| 500 | 500 | 166.6 ms | 12.9 ms |
| 1000 | 805 | 216.7 ms | 20.3 ms |

At 1000 requested instances the viewport/size guard admitted 805. This is the first capacity boundary in this layout and is reported rather than hidden.

## Culling

| Total | Visible | Frame p95 | Render prepare p95 |
|---:|---:|---:|---:|
| 200 | 200 | 83.4 ms | 3.4 ms |
| 1000 | 200 | 83.4 ms | 2.8 ms |
| 1000 | 50 | 33.4 ms | 1.9 ms |
| 5000 | 50 | 33.4 ms | 2.3 ms |

Frame cost follows visible instances well. Token culling still scans the full token array; it is viewport-bounded for drawing, but not backed by a spatial index.

## Repeated versus unique resources

| Unique assets | Logical GPU | Frame p95 |
|---:|---:|---:|
| 1 | 0.0625 MiB | 50.0 ms |
| 10 | 0.625 MiB | 50.0 ms |
| 100 | 6.25 MiB | 50.1 ms |

Logical texture memory scales with unique assets, not instances, confirming the Flyweight behavior.

## Teardown

- Animated instances after removal: 0
- Logical benchmark GPU bytes after removal: 0
- Retained hidden token nodes: 893

Textures are released, but token display nodes remain pooled at the peak size. That pool is currently unbounded and should be treated as a teardown/memory finding.
