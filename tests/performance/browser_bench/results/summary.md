# Browser Benchmark — real Chromium on the live map

## Run

```txt
host:           http://localhost:8007
viewport:       1366x768
headed:         False   gpu: on   cpu_throttle: 1.0x
run_seconds:    180
map_visible:    True
```

## Time to map visible (ms from navigation)

```txt
nav -> canvas mounted:       1113
nav -> manifest loaded:      1123
nav -> first chunk:          1123
nav -> realtime open:        1123
nav -> MAP VISIBLE:          1123
```

## FPS / stutter during pan + zoom

```txt
duration:           181s   gestures: 402
frames captured:    10851
fps avg:            60.0
fps p50:            59.9
fps 1% low:         59.5
frame ms p95/p99:   16.7 / 16.8
worst frame ms:     16.8
janky frames >33ms: 0.0%
long tasks:         0   total blocking: 0.0 ms
```

## Memory (8 GB machine budget)

```txt
JS heap idle / peak:       17.4 / 17.4 MB
browser RSS idle / peak:   130.7 / 134.4 MB
```
