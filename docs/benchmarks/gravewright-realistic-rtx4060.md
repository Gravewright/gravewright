# Gravewright realistic scene — RTX 4060

Executed on 13 August 2026 with NVIDIA GeForce RTX 4060, driver 32.0.15.9621, ANGLE/D3D11, hardware acceleration enabled, Chromium headed, viewport 1366×768, 10-second warm-up, and 30-second measurement.

## Workload

- real 5,000×5,000 JPEG map;
- 500 or 800 simultaneously visible tokens;
- visible name and two bars on every token;
- 150 walls and 12 dynamic lights;
- token vision and darkness 0.6;
- no fast-sprite shortcut;
- continuous pan and zoom gesture.

## Runs

| Tokens | Run | Frame p50 | Frame p95 | Frame p99 | Maximum | >33 ms | Valid |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 500 | 1 | 16.7 ms | 16.9 ms | 17.0 ms | 33.4 ms | 0.1% | yes |
| 500 | 2 | 16.7 ms | 16.9 ms | 33.2 ms | 116.3 ms | 1.2% | yes |
| 500 | 3 | 16.7 ms | 16.9 ms | 17.0 ms | 17.3 ms | 0.0% | yes |
| 800 | 1 | 16.7 ms | 33.3 ms | 50.0 ms | 66.7 ms | 6.2% | yes |
| 800 | 2 | 16.7 ms | 17.0 ms | 33.3 ms | 33.6 ms | 2.7% | yes |
| 800 | 3 | 16.7 ms | 33.2 ms | 49.9 ms | 66.5 ms | 5.7% | yes |

## Medians

| Visible tokens | Valid runs | Frame p50 | Frame p95 | Frame p99 | App render p95 |
|---:|---:|---:|---:|---:|---:|
| 500 | 3/3 | 16.7 ms | **16.9 ms** | 17.0 ms | 11.8 ms |
| 800 | 3/3 | 16.7 ms | **33.2 ms** | 49.9 ms | 22.0 ms |

Every run reported `document_hidden=false`, zero visibility changes, zero rAF gaps above 500 ms, all requested tokens visible, 12 lighting sources, and `fast_sprites=0`.

