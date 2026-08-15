# Gravewright Real Campaign Torture Test — run 1

## Verdict

**FAIL — Phase A.** The run completed without page errors, but frame pacing was far outside the product gate. The Andromeda Composite phase was not run because the protocol requires Phase A to pass first.

## Workload

- Chromium headed, six independent browser processes: 1 GM + 5 players
- 5000×5000 adaptive raster, 400 source tiles
- 150 regular tokens + 25 transparent animated fast-path tokens per client
- 750 walls, including 75 doors
- 40 lights, 8 particle emitters, fog and LOS enabled
- Deterministic A → B → C → A camera route
- 10 s warm-up, 180 s cold, 30 s cooldown, 180 s warm

## Results

| Client class | Phase | frame p95 | app_render p95 | render_prepare p95 |
|---|---:|---:|---:|---:|
| GM | Cold | 1016.5 ms | 137.3 ms | 10.8 ms |
| GM | Warm | 1016.9 ms | 140.1 ms | 11.1 ms |
| Players (range) | Cold | 416.2–416.7 ms | 133.2–136.0 ms | 10.9–11.6 ms |
| Players (range) | Warm | 384.1–400.0 ms | 126.9–129.8 ms | 9.4–10.2 ms |

The dominant measured subsystem was `app_render`, not `render_prepare`. Raster image decode also produced large cold-path stalls. Warm caches did not bring the workload near the 33.3 ms acceptable gate.

## What remained healthy

- No page/runtime errors.
- 25 fast sprites were retained per client.
- GM-guided scheduler debt remained 0 ms.
- Walls, doors, lights, fog, raster and tokens loaded together.
- Texture and blob caches stayed under their byte caps.

## Validity

`document.hidden` remained false and no visibility changes were observed. However, every client recorded rAF intervals above 500 ms, so the run is formally invalid for a clean frame-pacing baseline under section 32. It is still a valid failure signal: median player frames were approximately 250–266 ms and `app_render` alone was approximately 127–140 ms p95.

No benchmark result was cherry-picked. Repetitions 2–5 and Andromeda Composite were not run because the first required Phase A gate failed decisively.
