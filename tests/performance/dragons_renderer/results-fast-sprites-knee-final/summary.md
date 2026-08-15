# Optimized renderer knee — headed Chromium

Each point used one visible Chromium process, one shared animated source, a
10-second warm-up, and a 30-second measurement window. “Visible” means instances
that survived spatial culling and were actually submitted by the renderer;
“requested” is only the input population.

| Requested | Actually visible | Frame p95 | Callback p95 | App render p95 | Result |
|---:|---:|---:|---:|---:|---|
| 6,000 | 5,145 | 16.8 ms | 16.4 ms | 1.8 ms | within 60 Hz callback budget |
| 6,250 | 5,162 | 16.8 ms | 18.5 ms | 2.1 ms | first callback-budget crossing |
| 6,500 | 5,162 | 16.8 ms | 18.4 ms | 2.1 ms | crossing reproduced |

The optimized renderer's measured callback-budget knee lies between **5,145 and
5,162 simultaneously visible entities**, conventionally reported as
**approximately 5,150**. For release communication, **approximately 5,000
simultaneously visible entities** is the practical round-number target.

This is a budget knee, not a catastrophic frame collapse: the presentation
frame p95 remained in the 16.8 ms band, while the measured animation callback
was the first component to cross the 16.67 ms 60 Hz budget. The older 3,000
result belongs to the pre-optimization baseline and is not the Beta 1 ceiling.
