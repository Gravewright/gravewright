# WS Live Session — token / fog / chat / reconnect load

## Result

```txt
finished:            True
host:                http://app:8000
users:               18
run_time:            180s
actual_duration:     181.0s
users_started:       18
users_finished:      18
failures:            0
connection_failures: 0
```

## Realtime traffic

```txt
commands_sent:       4564
token_moves:         3273
fog_paints:          648
chat_messages:       206
rolls:               196
pan_zooms:           540
connections_opened:  103
reconnects:          86
resumes:             85
clean_resumes:       85
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
    "count": 3273.0,
    "avg": 4.524500622375941,
    "p50": 3.6425859998416854,
    "p95": 6.5349209999112645,
    "p99": 22.194877001311397,
    "max": 288.13753000031284
  },
  "fog_paint": {
    "count": 648.0,
    "avg": 3.8604636929757823,
    "p50": 2.8919850010424852,
    "p95": 5.848552000315976,
    "p99": 17.1818170001643,
    "max": 101.82208299920603
  },
  "chat": {
    "count": 402.0,
    "avg": 5.511642360685453,
    "p50": 3.976256000896683,
    "p95": 6.419434999770601,
    "p99": 62.03748099869699,
    "max": 191.8215269997745
  },
  "subscribe": {
    "count": 18.0,
    "avg": 90.4005441665908,
    "p50": 101.29971000060323,
    "p95": 126.05387199982943,
    "p99": 126.05387199982943,
    "max": 126.05387199982943
  },
  "resume": {
    "count": 85.0,
    "avg": 10.443983635195764,
    "p50": 9.321819999968284,
    "p95": 15.168429001278128,
    "p99": 40.41256199889176,
    "max": 40.41256199889176
  },
  "pan_zoom": {
    "count": 540.0,
    "avg": 6.7344519833871646,
    "p50": 5.9642919986799825,
    "p95": 11.436275999585632,
    "p99": 16.825642000185326,
    "max": 36.704074998851866
  }
}
```
