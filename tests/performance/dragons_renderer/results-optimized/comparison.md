# Token renderer optimization — headed before/after

Identical workload: one shared animated source, 10 s warm-up, 30 s measurement.

| Requested / visible | Frame p95 before | Frame p95 after | Callback before | Callback after | App render before | App render after |
|---|---:|---:|---:|---:|---:|---:|
| 250 / 250 | 16.9 ms | 16.9 ms | 7.7 ms | 6.4 ms | 4.0 ms | 4.1 ms |
| 500 / 500 | 16.9 ms | 17.0 ms | 12.3 ms | 6.6 ms | 8.7 ms | 3.8 ms |
| 750 / 710 | 16.9 ms | 17.0 ms | 17.1 ms | 7.5 ms | 12.2 ms | 5.3 ms |
| 1000 / 805 | 33.3 ms | 16.8 ms | 19.6 ms | 8.7 ms | 14.6 ms | 6.2 ms |

At 1000 requested / 805 visible, the optimization reduced callback p95 by 55.6% and app-render p95 by 57.5%, moving frame p95 from the 30 Hz band back to 60 Hz.

The change preserves circular masks and token decorations, but stores geometry in token-local coordinates and rebuilds it only when visual state changes. World movement is now a container transform. Nodes belonging to removed tokens are destroyed; merely offscreen nodes remain available and hidden.
