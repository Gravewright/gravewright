# Performance and benchmark methodology

Gravewright publishes raw benchmark artifacts together with the harnesses that produced them. Performance claims must name the workload, browser mode, viewport, hardware, warm-up, measurement window, and validity gates.

## Current reference machine

The latest renderer comparisons were executed on 13 August 2026 with:

- NVIDIA GeForce RTX 4060, driver 32.0.15.9621;
- Chromium headed using ANGLE over Direct3D 11;
- hardware acceleration enabled;
- viewport 1366×768;
- 10-second warm-up and 30-second measurement windows.

GPU identity and acceleration state are recorded in the raw JSON files. Headless frame cadence is not used as an acceptance result.

## Workloads

### Shared animated-token stress test

This synthetic workload uses one animated 128×128 canvas source shared by every dragon instance. Tokens use the dense fast-sprite path and are packed into the viewport. It measures instance scaling and shared-resource behavior; it does not represent a normal campaign scene or video decoding.

Current RTX 4060 observations:

| Visible dragons | Frame p95 | Animation callback p95 | Interpretation |
|---:|---:|---:|---|
| 100 | 16.9 ms | 9.2 ms | canonical baseline |
| 6,500 | 16.9 ms | 13.8 ms | approximately 60 Hz presentation |
| 7,500 | 17.0 ms | 12.2 ms | last measured point in the 60 Hz band |
| 10,000 | 33.5 ms | 15.5 ms | approximately 30 Hz presentation |
| 11,000 | 33.7 ms | 16.5 ms | callback still within 16.67 ms |
| 11,500 | 50.1 ms | 23.2 ms | callback budget crossed |

The presentation knee lies between 7,500 and 10,000 visible dragons. The isolated callback-budget crossing lies between 11,000 and 11,500. Near-limit sequential runs showed variance, so the project does not claim a single exact entity ceiling.

Raw data and discussion: [`tests/performance/dragons_renderer/results-gpu-rtx4060/summary.md`](../tests/performance/dragons_renderer/results-gpu-rtx4060/summary.md).

### Realistic 5K scene

This workload deliberately disables the fast-sprite shortcut. It uses a real 5,000×5,000 JPEG map, visible names and two bars on every token, 150 walls, 12 dynamic lights, token vision, and darkness 0.6.

| Visible tokens | Valid runs | Median frame p95 | Median frame p99 |
|---:|---:|---:|---:|
| 500 | 3/3 | 16.9 ms | 17.0 ms |
| 800 | 3/3 | 33.2 ms | 49.9 ms |

All runs confirmed the RTX 4060 and passed the visibility, workload, and rAF-gap gates. See the [RTX 4060 realistic-scene report](benchmarks/gravewright-realistic-rtx4060.md).

## Validity rules

A realistic-scene run is comparable only when:

- the browser is headed, focused, and visible;
- no visibility change occurs during measurement;
- no rAF gap exceeds 500 ms;
- the expected token, wall, light, and map counts are active;
- every requested token is actually visible;
- the Gravewright realistic test reports `fast_sprites=0`;
- hardware acceleration and the expected GPU are confirmed.

Invalid attempts are preserved for audit but excluded from medians. Setup failures, stale locks, login failures, and instrumentation defects must be documented separately from application-renderer failures.

## Interpreting the numbers

Do not compare the dragon ceiling directly with realistic-scene token counts. The dragon test is a best-case shared-asset stress test; the realistic test includes labels, bars, lighting, vision, walls, and map composition. Always quote the workload beside the number.
