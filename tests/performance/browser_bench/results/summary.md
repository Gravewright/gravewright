# Browser Benchmark — real Chromium on the live map

## Run

```txt
host:           http://localhost:8007
viewport:       1366x768
headed:         True   gpu: on   cpu_throttle: 1.0x
run_seconds:    180
map_visible:    False
```

## Time to map visible (ms from navigation)

```txt
nav -> canvas mounted:          0
nav -> manifest loaded:         0
nav -> first chunk:             0
nav -> realtime open:           0
nav -> MAP VISIBLE:             0
```

## FPS / stutter during pan + zoom

```txt
duration:           0s   gestures: 0
frames captured:    0
fps avg:            0.0
fps p50:            0.0
fps 1% low:         0.0
frame ms p95/p99:   0.0 / 0.0
worst frame ms:     0.0
janky frames >33ms: 0.0%
long tasks:         0   total blocking: 0.0 ms
```

## Memory (8 GB machine budget)

```txt
JS heap idle / peak:       0.0 / 0.0 MB
browser RSS idle / peak:   0.0 / 1123.1 MB
```

## Errors

```txt
Error: Page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:8007/
Call log:
  - navigating to "http://localhost:8007/", waiting until "domcontentloaded"

```
