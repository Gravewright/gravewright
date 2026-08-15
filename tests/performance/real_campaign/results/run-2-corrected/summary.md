# Gravewright Real Campaign Torture Test — corrected repeat

## Root cause

The first fixture incorrectly used the adaptive raster tile size (`256 px`) as the logical VTT grid size. A six-cell light therefore had a 1536 px world radius instead of the intended 420 px radius for a 70 px grid. Forty oversized overlapping lights drove Pixi `app_render` to 127–140 ms p95.

Component isolation on one headed Chromium confirmed:

- full broken fixture: frame p95 216.7 ms; `app_render` p95 75.5 ms;
- fog without lighting: frame p95 16.9 ms;
- lighting without fog: frame p95 200.0 ms; `app_render` p95 108.8 ms;
- raster + tokens without lighting/fog: frame p95 16.9 ms.

The fixture now uses a 70 px logical grid while retaining 256 px adaptive raster tiles. The renderer also culls light presentation objects that cannot influence the viewport; logical lights and LOS data remain scene-wide.

## Corrected repeat

| Client class | Phase | frame p95 | frame p99 | app_render p95 |
|---|---:|---:|---:|---:|
| GM | Cold | 34.5 ms | 50.4 ms | 12.1 ms |
| GM | Warm | 33.9 ms | 50.2 ms | 11.6 ms |
| Players median | Cold | 33.9 ms | 50.2 ms | 11.3–12.0 ms |
| Players median | Warm | 33.7 ms | 50.2 ms | 11.0–11.4 ms |

Five clients/phases had no rAF interval above 500 ms. Player 3 warm recorded six such intervals and that individual warm sample is invalid for frame pacing. No page errors occurred and `document.hidden` remained false for every client.

## Verdict

**Major root cause fixed; Phase A remains marginal FAIL.** The corrected build is close to the acceptable 33.3 ms p95 gate but does not meet it, and p99 remains around 50 ms. Scheduler debt stayed at 0 ms and the 25 animated fast-path sprites remained active per client.
