"""Summarize a tests/e2e/realtime_session.py run into report.json and report.md.

Server figures come from server-ops.jsonl (every realtime operation); browser figures
from client.jsonl (every frame sent or received, timestamped in the page). The
"0.3.5 log view" reproduces what the stock slow-handler warning would have shown:
deliveries and peer samples without queue time, and only operations >= 500 ms.

    uv run --locked python tests/e2e/realtime_session_report.py <run-directory>
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SLOW_MS = 500
PEER_SAMPLES = {"room.map_cursor", "room.token_drag"}
COMMAND_TYPES = {"tokens.command", "actors.command", "chat.say", "dice.roll",
                 "resources.command", "maps.command", "journals.command"}


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def pct(values, p):
    values = sorted(values)
    if not values:
        return None
    index = max(0, min(len(values) - 1, round(p / 100 * len(values) + 0.5) - 1))
    return values[index]


def summary(values):
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0}
    return {"n": len(values), "p50": round(pct(values, 50), 1), "p95": round(pct(values, 95), 1),
            "max": round(max(values), 1)}


def total(op):
    return op["queue_ms"] + op["handler_ms"]


def logged_queue(op):
    """Queue time as 0.3.5 reports it (deliveries and peer samples show 0)."""
    if op["kind"] == "delivery" or (op["kind"] == "ephemeral" and op["name"] in PEER_SAMPLES):
        return 0.0
    return op["queue_ms"]


def server_section(ops, window):
    start, end = window
    play = [op for op in ops if start <= op["t"] <= end]
    groups = defaultdict(list)
    for op in play:
        groups[(op["kind"], op["name"])].append(op)
    by_name = []
    for (kind, name), rows in sorted(groups.items(), key=lambda item: -sum(r["handler_ms"] for r in item[1])):
        by_name.append({
            "kind": kind, "name": name, "n": len(rows),
            "total_ms": summary([total(r) for r in rows]),
            "queue_ms": summary([r["queue_ms"] for r in rows]),
            "handler_ms": summary([r["handler_ms"] for r in rows]),
            "sql_count": summary([r["sql_count"] for r in rows]),
            "busy_s": round(sum(r["handler_ms"] for r in rows) / 1000, 1),
        })

    def breakdown(rows):
        handler = sum(r["handler_ms"] for r in rows) or 1
        sync = sum(r["sync_ms"] for r in rows)
        sql = sum(r["sql_ms"] for r in rows)
        cpu = sum(r["sync_cpu_ms"] for r in rows)
        wait = sum(r["sync_wait_ms"] for r in rows)
        return {
            "n": len(rows), "handler_s": round(handler / 1000, 1),
            "waiting_for_thread_pct": round(100 * wait / handler, 1),
            "running_in_thread_pct": round(100 * sync / handler, 1),
            "sql_pct": round(100 * sql / handler, 1),
            "thread_cpu_pct": round(100 * cpu / handler, 1),
            "outside_sql_pct": round(100 * (1 - sql / handler), 1),
            "non_sql_thread_wall_ms_per_op": round((sync - sql) / max(1, len(rows)), 1),
            "thread_cpu_ms_per_op": round(cpu / max(1, len(rows)), 1),
        }

    commands = [op for op in play if op["kind"] == "command"]
    changes = [op for op in play if op["kind"] == "delivery" and op["name"] == "room.changes"]
    gm_samples = [op for op in play if op["kind"] == "delivery" and op["name"] == "room.gm_sample"]
    presence = [op for op in play if op["kind"] == "presence"]
    slow = [op for op in play if logged_queue(op) + op["handler_ms"] >= SLOW_MS]
    slow_commands = [op for op in slow if op["kind"] == "command"]
    short_reads = [op for op in slow if 1 <= op["sql_count"] <= 5]
    log_view = {
        "slow_operations": len(slow),
        "lock_errors": sum(op["lock_errors"] for op in play),
        "slow_commands": {"total": len(slow_commands),
                          **{f"over_{s}s": sum(total(op) > s * 1000 for op in slow_commands) for s in (1, 5, 10, 20)}},
        "worst_commands": [{"name": op["name"], "conn": op["conn"], "queue_ms": op["queue_ms"],
                            "handler_ms": op["handler_ms"]}
                           for op in sorted(commands, key=total, reverse=True)[:5]],
        "room_changes_slow": {
            "n": sum(op["handler_ms"] >= SLOW_MS for op in changes),
            "handler_ms": summary([op["handler_ms"] for op in changes if op["handler_ms"] >= SLOW_MS]),
            "sql_count": summary([op["sql_count"] for op in changes if op["handler_ms"] >= SLOW_MS]),
        },
        "gm_sample_slow": {
            "n": sum(op["handler_ms"] >= SLOW_MS for op in gm_samples),
            "handler_ms": summary([op["handler_ms"] for op in gm_samples if op["handler_ms"] >= SLOW_MS]),
        },
        "presence_slow": summary([op["handler_ms"] for op in presence if op["handler_ms"] >= SLOW_MS]),
        "short_reads_over_100ms_per_query": [
            sum(op["sql_ms"] / op["sql_count"] > 100 for op in short_reads), len(short_reads)],
    }
    complete = {
        "room_changes": {
            "n": len(changes), "queue_ms": summary([op["queue_ms"] for op in changes]),
            "handler_ms": summary([op["handler_ms"] for op in changes]),
            "total_ms": summary([total(op) for op in changes]),
            "sql_count": summary([op["sql_count"] for op in changes]),
            "time": breakdown(changes),
        },
        "room_gm_sample": {
            "n": len(gm_samples), "queue_ms": summary([op["queue_ms"] for op in gm_samples]),
            "handler_ms": summary([op["handler_ms"] for op in gm_samples]),
            "sql_count": summary([op["sql_count"] for op in gm_samples]),
            "command_lane_busy_s": round(sum(op["handler_ms"] for op in gm_samples) / 1000, 1),
        },
        "commands": {"total_ms": summary([total(op) for op in commands]),
                     "queue_ms": summary([op["queue_ms"] for op in commands]),
                     "handler_ms": summary([op["handler_ms"] for op in commands]),
                     "sql_count": summary([op["sql_count"] for op in commands]),
                     "time": breakdown(commands)},
        "presence": {"handler_ms": summary([op["handler_ms"] for op in presence]),
                     "over_5s": sum(op["handler_ms"] > 5000 for op in presence),
                     "over_8s": sum(op["handler_ms"] > 8000 for op in presence),
                     "time": breakdown(presence)},
        "ephemeral_queue_ms": {name: summary([op["queue_ms"] for op in play
                                              if op["kind"] == "ephemeral" and op["name"] == name])
                               for name in ("maps.cursor", "scene.viewport", "token.drag",
                                            "room.map_cursor", "room.token_drag")},
        "heartbeat": {"handler_ms": summary([op["handler_ms"] for op in play if op["kind"] == "heartbeat"]),
                      "time": breakdown([op for op in play if op["kind"] == "heartbeat"])},
        # Median SQL time per statement, over all operations and over the >= 500 ms ones
        # (the only ones a 0.3.5 log contains), so runs compare with a stock log.
        "sql_ms_per_query": {
            name: {"all": summary([op["sql_ms"] / op["sql_count"] for op in rows if op["sql_count"]]),
                   "slow": summary([op["sql_ms"] / op["sql_count"] for op in rows
                                    if op["sql_count"] and logged_queue(op) + op["handler_ms"] >= SLOW_MS])}
            for name, rows in {
                "room.changes": changes, "room.gm_sample": gm_samples, "presence": presence,
                "room.map_cursor": [op for op in play if op["name"] == "room.map_cursor"],
                "scene.viewport": [op for op in play if op["name"] == "scene.viewport"],
            }.items()
        },
    }
    per_connection = {}
    for conn in sorted({op["conn"] for op in play}):
        rows = [op for op in play if op["conn"] == conn]
        per_connection[conn] = {
            "command_total_ms": summary([total(op) for op in rows if op["kind"] == "command"]),
            "delivery_queue_ms": summary([op["queue_ms"] for op in rows if op["kind"] == "delivery"]),
            "deliveries": sum(op["kind"] == "delivery" for op in rows),
            "command_lane_busy_s": round(sum(op["handler_ms"] for op in rows
                                             if op["kind"] in ("command", "delivery")) / 1000, 1),
        }
    timeline = []
    bucket = 30
    for at in range(int(start), int(end) + 1, bucket):
        rows = [op for op in play if at <= op["t"] < at + bucket]
        timeline.append({
            "minute": round((at - start) / 60, 1), "ops": len(rows),
            "command_max_ms": round(max([total(op) for op in rows if op["kind"] == "command"], default=0)),
            "delivery_queue_max_ms": round(max([op["queue_ms"] for op in rows if op["kind"] == "delivery"], default=0)),
            "changes": sum(op["name"] == "room.changes" for op in rows),
        })
    return {"by_name": by_name, "log_view": log_view, "complete": complete,
            "per_connection": per_connection, "timeline": timeline}


def client_section(records, window):
    start, end = (window[0] * 1000, window[1] * 1000)
    labels = sorted({r["label"] for r in records})
    play = [r for r in records if start <= r["t"] <= end + 5000]
    sends = [r for r in play if r["ev"] == "send"]
    recvs = [r for r in play if r["ev"] == "recv"]
    by_label = defaultdict(list)
    for r in recvs:
        by_label[r["label"]].append(r)

    # Command round trips: first acknowledgement for the request id (busy retries keep it).
    rtt, errors = defaultdict(list), Counter()
    acks = {}
    for r in recvs:
        if r.get("rid"):
            if r["type"].endswith(".ack"):
                acks.setdefault((r["label"], r["rid"]), r["t"])
            elif r.get("code"):
                errors[(r["type"], r["code"])] += 1
    seen = set()
    for r in sends:
        if r["type"] in COMMAND_TYPES and r.get("rid") and (r["label"], r["rid"]) not in seen:
            seen.add((r["label"], r["rid"]))
            done = acks.get((r["label"], r["rid"]))
            key = r["type"] + (":" + r["action"] if r.get("action") else "")
            rtt[key].append(done - r["t"] if done else None)
    round_trips = {key: {**summary(values), "unanswered": sum(v is None for v in values)}
                   for key, values in sorted(rtt.items())}

    def first_after(label, t0, predicate, horizon=60_000):
        for r in by_label[label]:
            if t0 <= r["t"] <= t0 + horizon and predicate(r):
                return r["t"] - t0
        return None

    moves = defaultdict(list)
    for r in sends:
        if r["type"] == "tokens.command" and r.get("move"):
            token, x, y = r["move"]
            for label in labels:
                moves["sender" if label == r["label"] else "others"].append(first_after(
                    label, r["t"], lambda q: q["type"] == "tokens.state" and any(
                        row[0] == token and row[1] == x and row[2] == y for row in q.get("tk", []))))
    chat = []
    for r in sends:
        if r["type"] == "chat.say" and r.get("mark"):
            for label in labels:
                if label != r["label"]:
                    chat.append(first_after(label, r["t"], lambda q: q["type"] == "chat.message" and q.get("mark") == r["mark"]))

    def peer(kind, send_ok, match):
        latencies, attempts = [], 0
        for r in sends:
            if r["type"] == kind and send_ok(r):
                for label in labels:
                    if label != r["label"]:
                        attempts += 1
                        value = first_after(label, r["t"], lambda q: q["type"] == kind and match(r, q), 30_000)
                        if value is not None:
                            latencies.append(value)
        return {**summary(latencies), "delivered_pct": round(100 * len(latencies) / max(1, attempts), 1)}

    cursor = peer("maps.cursor", lambda r: r.get("pos"), lambda r, q: q.get("pos") == r["pos"])
    drag = peer("token.drag", lambda r: r.get("phase") == "update" and r.get("pos"),
                lambda r, q: q.get("stream") == r.get("stream") and q.get("pos") == r["pos"])
    pings, presence, frames, closes, hints = {}, {}, defaultdict(int), [], Counter()
    for label in labels:
        times = [r["t"] for r in by_label[label] if r["type"] == "session.ping"]
        gaps = [b - a for a, b in zip(times, times[1:])]
        pings[label] = {"max_gap_s": round(max(gaps, default=0) / 1000, 1),
                        "gaps_over_7s": sum(g > 7000 for g in gaps)}
        counts = [r["n"] for r in by_label[label] if r["type"] == "table.presence" and "n" in r]
        presence[label] = {"updates": len(counts), "drops": sum(b < a for a, b in zip(counts, counts[1:])),
                           "min": min(counts, default=None)}
        for r in by_label[label]:
            frames[r["type"]] = max(frames[r["type"]], r["bytes"])
            if r["type"] in ("scene.gm_prefetch.hint", "scene.viewport.ready"):
                hints[(label, r["type"])] += 1
    for r in records:
        if r["ev"] == "close":
            closes.append({"label": r["label"], "code": r.get("code"), "t_min": round((r["t"] - start) / 60000, 2)})
    minutes = max(1e-9, (end - start) / 60000)
    sent_rates = defaultdict(dict)
    for (label, kind), n in Counter((r["label"], r["type"]) for r in sends).items():
        sent_rates[label][kind] = round(n / minutes, 1)
    return {
        "round_trips": round_trips,
        "errors": {f"{k[0]}:{k[1]}": v for k, v in errors.items()},
        "token_move_seen_by": {k: {**summary(v), "missing": sum(x is None for x in v)} for k, v in moves.items()},
        "chat_seen_by_others": {**summary(chat), "missing": sum(x is None for x in chat)},
        "cursor_peer": cursor, "drag_peer": drag, "pings": pings, "presence": presence,
        "largest_frames": dict(sorted(frames.items(), key=lambda kv: -kv[1])[:8]),
        "closes": closes, "stream_events": {f"{k[0]}:{k[1]}": v for k, v in hints.items()},
        "sent_per_minute": sent_rates,
    }


def http_section(requests, window):
    start, end = window[0] * 1000, window[1] * 1000
    play = [r for r in requests if start <= r["t"] <= end]
    groups = defaultdict(list)
    for r in play:
        groups[(r["method"], r["path"])].append(r)
    minutes = max(1e-9, (end - start) / 60000)
    return {
        "per_minute": round(len(play) / minutes, 1),
        "failed": sum(r.get("failed", False) for r in play),
        "by_path": [{"request": f"{m} {p}", "per_minute": round(len(rows) / minutes, 2),
                     **summary([r["ms"] for r in rows])}
                    for (m, p), rows in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:15]],
    }


def cpu_section(samples, window):
    rows = [r for r in samples if window[0] <= r["t"] <= window[1]]
    return {"process_cpu": summary([r["process_cpu"] * 100 for r in rows]),
            "busiest_thread": summary([r["top_threads"][0] * 100 for r in rows if r["top_threads"]]),
            "threads": summary([r["threads"] for r in rows]),
            "machine_busy": summary([r["machine_busy"] * 100 for r in rows if r.get("machine_busy") is not None])}


def fmt(s, key="p50"):
    return "-" if not s or s.get("n", 0) == 0 else f"{s[key]:.0f}"


def markdown(report):
    s, c, meta = report["server"], report["client"], report["meta"]
    lv, cp = s["log_view"], s["complete"]
    events = meta.get("events", [])
    start = next((e["t"] for e in events if e["event"] == "play-start"), None)
    marks = ", ".join(f"{e['event']}{':' + str(e.get('target') or e.get('label')) if e.get('target') or e.get('label') else ''}"
                      f"@{(e['t'] - start) / 60:.1f}min{'' if e.get('ok', True) else ' FAILED'}"
                      for e in events if start and e["t"] > start and e["event"] not in ("play-end",))
    lines = [f"# Realtime session {meta['run']}", "",
             f"{meta['participants']} · play {meta['minutes']:.1f} min · journal_mode={meta['journal_mode']} · commit {meta['git']}", "",
             f"Events: {marks or 'none'}", "",
             "## 0.3.5 log view (deliveries without queue time, >= 500 ms)", "",
             "| Signal | Value |", "| --- | --- |",
             f"| Slow operations | {lv['slow_operations']} (lock_errors={lv['lock_errors']}) |",
             f"| Slow commands | {lv['slow_commands']['total']}: >1 s {lv['slow_commands']['over_1s']}, >5 s {lv['slow_commands']['over_5s']}, >10 s {lv['slow_commands']['over_10s']}, >20 s {lv['slow_commands']['over_20s']} |",
             f"| Slow room.changes | {lv['room_changes_slow']['n']}; median {fmt(lv['room_changes_slow']['handler_ms'])} ms, max {fmt(lv['room_changes_slow']['handler_ms'], 'max')} ms |",
             f"| Slow room.gm_sample | {lv['gm_sample_slow']['n']}; median {fmt(lv['gm_sample_slow']['handler_ms'])} ms |",
             f"| Slow presence renewals | {lv['presence_slow'].get('n', 0)}; max {fmt(lv['presence_slow'], 'max')} ms |",
             f"| Short reads (<= 5 SQL) > 100 ms/query | {lv['short_reads_over_100ms_per_query'][0]} of {lv['short_reads_over_100ms_per_query'][1]} |",
             "", "## Complete server view", "", "| Path | n | queue p50/p95/max ms | handler p50/p95/max ms | SQL p50/max |",
             "| --- | --- | --- | --- | --- |"]
    for label, key in (("commands", "commands"), ("room.changes", "room_changes"), ("room.gm_sample", "room_gm_sample")):
        row = cp[key]
        queue = row["queue_ms"]
        handler = row.get("handler_ms", row.get("total_ms"))
        sql = row.get("sql_count", {"n": 0})
        lines.append(f"| {label} | {queue.get('n', 0)} | {fmt(queue)}/{fmt(queue, 'p95')}/{fmt(queue, 'max')} | "
                     f"{fmt(handler)}/{fmt(handler, 'p95')}/{fmt(handler, 'max')} | {fmt(sql)}/{fmt(sql, 'max')} |")
    t = cp["room_changes"]["time"]
    lines += ["", f"room.changes time: SQL {t['sql_pct']}%, outside SQL {t['outside_sql_pct']}%, waiting for the socket thread {t['waiting_for_thread_pct']}%, thread CPU {t['thread_cpu_pct']}%; "
              f"per delivery, non-SQL thread wall {t['non_sql_thread_wall_ms_per_op']} ms vs thread CPU {t['thread_cpu_ms_per_op']} ms.",
              f"room.gm_sample kept the command lanes busy for {cp['room_gm_sample']['command_lane_busy_s']} s.",
              f"Presence renewals: p50 {fmt(cp['presence']['handler_ms'])} ms, max {fmt(cp['presence']['handler_ms'], 'max')} ms, >5 s {cp['presence']['over_5s']}, >8 s {cp['presence']['over_8s']}.",
              "", "SQL ms per statement (median, all / >= 500 ms ops): " + ", ".join(
                  f"{name} {fmt(v['all'])}/{fmt(v['slow'])}" if v["all"].get("n") and v["all"]["p50"] >= 1
                  else f"{name} {v['all'].get('p50', '-')}/{v['slow'].get('p50', '-')}"
                  for name, v in cp["sql_ms_per_query"].items()),
              f"HTTP from browsers: {report['http']['per_minute']} requests/min, failed {report['http']['failed']}; "
              + "; ".join(f"{r['request']} {r['per_minute']}/min p50 {fmt(r)} ms" for r in report["http"]["by_path"][:6]) + ".",
              "", "## Browser view", "", "| Measure | n | p50 ms | p95 ms | max ms |", "| --- | --- | --- | --- | --- |"]
    for key, value in c["round_trips"].items():
        lines.append(f"| RTT {key} | {value.get('n', 0)} | {fmt(value)} | {fmt(value, 'p95')} | {fmt(value, 'max')} |")
    for key, value in c["token_move_seen_by"].items():
        lines.append(f"| Token move seen by {key} | {value.get('n', 0)} | {fmt(value)} | {fmt(value, 'p95')} | {fmt(value, 'max')} |")
    for key, label in (("chat_seen_by_others", "Chat seen by others"), ("cursor_peer", "Cursor at peers"), ("drag_peer", "Drag at peers")):
        value = c[key]
        lines.append(f"| {label} | {value.get('n', 0)} | {fmt(value)} | {fmt(value, 'p95')} | {fmt(value, 'max')} |")
    lines += ["", f"Pings: {json.dumps(c['pings'])}", f"Presence: {json.dumps(c['presence'])}",
              f"Errors: {json.dumps(c['errors'])}", f"Closes: {json.dumps(c['closes'])}",
              f"Server CPU %: {json.dumps(report['cpu'])}", "", "## Timeline (30 s)", "",
              "| min | ops | worst command ms | worst delivery queue ms | room.changes |", "| --- | --- | --- | --- | --- |"]
    for row in s["timeline"]:
        lines.append(f"| {row['minute']} | {row['ops']} | {row['command_max_ms']} | {row['delivery_queue_max_ms']} | {row['changes']} |")
    lines += ["", "## Top operations by handler time", "", "| kind | name | n | total p50/p95/max ms | queue p95 | SQL p50 | busy s |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in s["by_name"][:18]:
        lines.append(f"| {row['kind']} | {row['name']} | {row['n']} | {fmt(row['total_ms'])}/{fmt(row['total_ms'], 'p95')}/{fmt(row['total_ms'], 'max')} | "
                     f"{fmt(row['queue_ms'], 'p95')} | {fmt(row['sql_count'])} | {row['busy_s']} |")
    return "\n".join(lines) + "\n"


def main():
    run = Path(sys.argv[1]).resolve()
    meta = json.loads((run / "meta.json").read_text())
    events = {e["event"]: e["t"] for e in meta.get("events", [])}
    ops = read_jsonl(run / "server-ops.jsonl")
    window = (events.get("play-start", min((o["t"] for o in ops), default=0)),
              events.get("play-end", max((o["t"] for o in ops), default=0)))
    report = {
        "meta": {"run": run.name, "journal_mode": meta.get("journal_mode"), "git": meta.get("git"),
                 "participants": ", ".join(p["label"] for p in meta.get("participants", [])),
                 "minutes": (window[1] - window[0]) / 60, "events": meta.get("events", []),
                 "page_errors": meta.get("page_errors", {})},
        "server": server_section(ops, window),
        "client": client_section(read_jsonl(run / "client.jsonl"), window),
        "cpu": cpu_section(read_jsonl(run / "cpu.jsonl"), window),
        "http": http_section(read_jsonl(run / "client-http.jsonl"), window),
        "actions": dict(Counter(f"{a['label']}:{a['kind']}:{'ok' if a.get('ok') else 'fail'}"
                                for a in read_jsonl(run / "actions.jsonl"))),
    }
    server_log = run / "server.log"
    if server_log.exists():
        text = server_log.read_text(encoding="utf-8", errors="replace")
        report["server"]["log_errors"] = text.count(" ERROR ") + text.count("Traceback")
    (run / "report.json").write_text(json.dumps(report, indent=2))
    (run / "report.md").write_text(markdown(report))
    print(markdown(report))


if __name__ == "__main__":
    main()
