# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               500
run_time:            1200s
actual_duration:     1212.0s
users_started:       500
users_finished:      500
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       296945
token_moves:         241659
fog_paints:          48131
chat_messages:       14906
rolls:               15151
connections_opened:  7155
reconnects:          6668
resumes:             6655
clean_resumes:       6655
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
    "count": 241659.0,
    "avg": 504.00983102039044,
    "p50": 439.6932760009804,
    "p95": 787.8133920003165,
    "p99": 1981.6006349992676,
    "max": 6348.565739999685
  },
  "fog_paint": {
    "count": 48131.0,
    "avg": 433.71810434073734,
    "p50": 400.53458400143427,
    "p95": 682.478254999296,
    "p99": 1102.076870000019,
    "max": 6685.12961200031
  },
  "chat": {
    "count": 30057.0,
    "avg": 5565.026814995175,
    "p50": 5492.571016000511,
    "p95": 7341.007699000329,
    "p99": 8412.47309299979,
    "max": 11867.603938000684
  },
  "subscribe": {
    "count": 500.0,
    "avg": 291.6349641839951,
    "p50": 257.34298799943645,
    "p95": 615.3020190013194,
    "p99": 727.4072609998257,
    "max": 828.475274000084
  },
  "resume": {
    "count": 6655.0,
    "avg": 603.3670853609359,
    "p50": 529.9902800015843,
    "p95": 895.4470699991361,
    "p99": 2314.1142839995155,
    "max": 7201.637466001557
  }
}
```
