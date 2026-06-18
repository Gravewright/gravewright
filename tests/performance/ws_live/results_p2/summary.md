# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               500
run_time:            180s
actual_duration:     191.9s
users_started:       500
users_finished:      500
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       31860
token_moves:         25835
fog_paints:          4989
chat_messages:       1537
rolls:               1564
connections_opened:  1036
reconnects:          550
resumes:             536
clean_resumes:       536
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
    "count": 25835.0,
    "avg": 540.9429333244728,
    "p50": 477.81473100076255,
    "p95": 974.995303000469,
    "p99": 2149.3846379999013,
    "max": 5774.281689000418
  },
  "fog_paint": {
    "count": 4989.0,
    "avg": 472.6440560256571,
    "p50": 442.14871599979233,
    "p95": 764.2630169993936,
    "p99": 2009.8187559997314,
    "max": 5490.250153001398
  },
  "chat": {
    "count": 3101.0,
    "avg": 7446.0710131583355,
    "p50": 7338.984329000596,
    "p95": 11990.771122998922,
    "p99": 12667.299689001084,
    "max": 14735.068661000696
  },
  "subscribe": {
    "count": 500.0,
    "avg": 377.09531796394003,
    "p50": 293.3374639997055,
    "p95": 826.6533379992325,
    "p99": 1027.9869930000132,
    "max": 2251.1220750002394
  },
  "resume": {
    "count": 536.0,
    "avg": 697.4121470914167,
    "p50": 612.1312849991227,
    "p95": 1162.6733070006594,
    "p99": 4315.5684510002175,
    "max": 5027.071170999989
  }
}
```
