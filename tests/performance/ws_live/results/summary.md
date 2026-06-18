# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               15
run_time:            1200s
actual_duration:     1205.5s
users_started:       15
users_finished:      15
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       11968
token_moves:         9743
fog_paints:          1942
chat_messages:       596
rolls:               616
connections_opened:  283
reconnects:          269
resumes:             268
clean_resumes:       268
resync_required:     0
version_conflicts:   0
command_timeouts:    0
http_failures:       0
errors_by_code:      {}
```

## Latency (ms)

```json
{
  "token_move": {
    "count": 9743.0,
    "avg": 791.7885068168981,
    "p50": 5.669719999787048,
    "p95": 4781.8585759996495,
    "p99": 4989.722889999939,
    "max": 5729.829331000474
  },
  "fog_paint": {
    "count": 1942.0,
    "avg": 22.337379469631504,
    "p50": 7.015964999482094,
    "p95": 42.3847210004169,
    "p99": 114.26814600054058,
    "max": 5013.072726999781
  },
  "chat": {
    "count": 1212.0,
    "avg": 11.53147796947784,
    "p50": 4.636738999579393,
    "p95": 29.942498999844247,
    "p99": 63.69537999944441,
    "max": 865.0546879998728
  },
  "subscribe": {
    "count": 15.0,
    "avg": 144.2389757335453,
    "p50": 165.5201119992853,
    "p95": 170.78498400042008,
    "p99": 170.78498400042008,
    "max": 170.78498400042008
  },
  "resume": {
    "count": 268.0,
    "avg": 670.2853045074897,
    "p50": 31.857088999458938,
    "p95": 4746.321261000048,
    "p99": 4969.630810999661,
    "max": 5183.683829999609
  }
}
```
