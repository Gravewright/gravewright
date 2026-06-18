# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               500
run_time:            180s
actual_duration:     193.3s
users_started:       500
users_finished:      500
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       28064
token_moves:         22787
fog_paints:          4344
chat_messages:       1369
rolls:               1318
connections_opened:  933
reconnects:          447
resumes:             433
clean_resumes:       433
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
    "count": 22787.0,
    "avg": 946.6863040287394,
    "p50": 922.6945690006687,
    "p95": 1554.970109000351,
    "p99": 2669.020545999956,
    "max": 6449.1531739986385
  },
  "fog_paint": {
    "count": 4344.0,
    "avg": 545.8388467872967,
    "p50": 518.6998330009374,
    "p95": 854.5575330008433,
    "p99": 2346.1844579996978,
    "max": 5792.106434000743
  },
  "chat": {
    "count": 2687.0,
    "avg": 7581.731579690341,
    "p50": 7570.780804999231,
    "p95": 11788.562730000194,
    "p99": 12577.085537999665,
    "max": 14028.230797001015
  },
  "subscribe": {
    "count": 500.0,
    "avg": 468.55607338000846,
    "p50": 399.94530100011616,
    "p95": 943.1448819996149,
    "p99": 1125.366557000234,
    "max": 1253.8892130014574
  },
  "resume": {
    "count": 433.0,
    "avg": 799.5985646697251,
    "p50": 748.605488000976,
    "p95": 1256.2390139992203,
    "p99": 2762.6044349999574,
    "max": 4562.391586001468
  }
}
```
