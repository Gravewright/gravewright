# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               500
run_time:            1200s
actual_duration:     1211.3s
users_started:       500
users_finished:      500
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       247552
token_moves:         201397
fog_paints:          40102
chat_messages:       12511
rolls:               12510
connections_opened:  6053
reconnects:          5565
resumes:             5553
clean_resumes:       5553
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
    "count": 201397.0,
    "avg": 879.4478706073813,
    "p50": 834.4198169997981,
    "p95": 1247.264533998532,
    "p99": 1617.9924999996729,
    "max": 7003.989277000073
  },
  "fog_paint": {
    "count": 40102.0,
    "avg": 494.5449958704295,
    "p50": 468.8663969991467,
    "p95": 710.690820000309,
    "p99": 906.8657509997138,
    "max": 5730.10893799983
  },
  "chat": {
    "count": 25021.0,
    "avg": 6105.879718546777,
    "p50": 6003.728809000677,
    "p95": 8207.303861001492,
    "p99": 9212.588581000091,
    "max": 13808.79410399939
  },
  "subscribe": {
    "count": 500.0,
    "avg": 406.59556493796475,
    "p50": 360.24095700122416,
    "p95": 882.5046519996249,
    "p99": 1029.2090809998626,
    "max": 1132.078371998432
  },
  "resume": {
    "count": 5553.0,
    "avg": 715.7887414136401,
    "p50": 679.6649959997012,
    "p95": 1012.140423999881,
    "p99": 1387.7335080014745,
    "max": 5928.8941330014495
  }
}
```
