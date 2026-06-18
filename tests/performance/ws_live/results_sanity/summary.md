# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               500
run_time:            45s
actual_duration:     76.1s
users_started:       401
users_finished:      401
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       3133
token_moves:         2304
fog_paints:          338
chat_messages:       56
rolls:               61
connections_opened:  401
reconnects:          0
resumes:             0
clean_resumes:       0
resync_required:     0
version_conflicts:   0
command_timeouts:    190
http_failures:       84
errors_by_code:      {}
```

## Latency (ms)

```json
{
  "token_move": {
    "count": 2304.0,
    "avg": 1759.861006378032,
    "p50": 1707.2799850002411,
    "p95": 3836.5908790001413,
    "p99": 3982.246481999937,
    "max": 4111.140224999872
  },
  "fog_paint": {
    "count": 338.0,
    "avg": 1147.0681957544405,
    "p50": 1266.3871370004927,
    "p95": 2281.4702559999205,
    "p99": 2447.6085400001466,
    "max": 2504.992841000785
  },
  "chat": {
    "count": 117.0,
    "avg": 2920.4606229486594,
    "p50": 2049.0975170005186,
    "p95": 12574.32189499923,
    "p99": 13666.293608999695,
    "max": 13848.083490000135
  },
  "subscribe": {
    "count": 301.0,
    "avg": 1025.0524966112823,
    "p50": 659.3523939991428,
    "p95": 2189.8143739999796,
    "p99": 2336.5283049997743,
    "max": 2402.019477999602
  },
  "resume": {
    "count": 0,
    "avg": 0,
    "p50": 0,
    "p95": 0,
    "p99": 0,
    "max": 0
  }
}
```
