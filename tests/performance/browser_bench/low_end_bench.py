#!/usr/bin/env python3
"""Run a reproducible low-end browser matrix and aggregate its results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from browser_bench import FIXTURES_PATH, run


LIMITS = {
    "frame_ms_p95": 33.0,
    "fps_1pct_low": 25.0,
    "jank_frame_pct": 2.0,
    "browser_rss_peak": 900.0,
}


def verdict(summary: dict, enforce: bool) -> tuple[str, list[str]]:
    failures: list[str] = []
    interaction = summary.get("interaction", {})
    memory = summary.get("memory_mb", {})
    if not summary.get("map_visible"):
        failures.append("map did not become visible")
    if interaction.get("frame_ms_p95", 0) > LIMITS["frame_ms_p95"]:
        failures.append(f"frame p95 {interaction['frame_ms_p95']}ms > 33ms")
    if interaction.get("fps_1pct_low", 0) < LIMITS["fps_1pct_low"]:
        failures.append(f"1% low {interaction['fps_1pct_low']}fps < 25fps")
    if interaction.get("jank_frame_pct", 0) > LIMITS["jank_frame_pct"]:
        failures.append(f"jank {interaction['jank_frame_pct']}% > 2%")
    rss = memory.get("browser_rss_peak", 0)
    if memory.get("rss_available") and rss > LIMITS["browser_rss_peak"]:
        failures.append(f"browser RSS {rss}MB > 900MB")
    if summary.get("errors"):
        failures.extend(summary["errors"])
    return ("fail" if failures and enforce else "observed", failures) if failures else ("pass", [])


def write_report(output: Path, rows: list[dict]) -> None:
    (output / "matrix.json").write_text(json.dumps({"limits": LIMITS, "runs": rows}, indent=2), encoding="utf-8")
    lines = [
        "# Low-end browser benchmark", "",
        "| Profile | CPU | FPS avg | 1% low | p95 ms | p99 ms | Jank | RSS peak | Result |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        i, m = row["interaction"], row["memory_mb"]
        lines.append(
            f"| {row['graphics_profile']} | {row['cpu_throttle']}× | {i['fps_avg']} | "
            f"{i['fps_1pct_low']} | {i['frame_ms_p95']} | {i['frame_ms_p99']} | "
            f"{i['jank_frame_pct']}% | {m['browser_rss_peak']} MB | {row['verdict']} |"
        )
    lines += ["", "Limits are enforced only for the low profile at the selected baseline throttle.", ""]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8007")
    parser.add_argument("--email", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--fixtures", default=str(FIXTURES_PATH))
    parser.add_argument("--profiles", nargs="+", choices=["low", "medium", "high"], default=["low", "medium", "high"])
    parser.add_argument("--throttles", nargs="+", type=float, default=[1, 4, 6])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--load-timeout", type=float, default=60)
    parser.add_argument("--baseline-throttle", type=float, default=4)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--gpu", choices=["on", "off"], default="on")
    parser.add_argument("--width", type=int, default=1366)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--output", default="tests/performance/browser_bench/results-low-end")
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    failed = False
    for profile in args.profiles:
        for throttle in args.throttles:
            run_dir = output / f"{profile}-cpu-{throttle:g}x"
            bench_args = SimpleNamespace(
                host=args.host, email=args.email, password=args.password, fixtures=args.fixtures,
                time=0.0, duration=args.duration, load_timeout=args.load_timeout,
                headed=args.headed, gpu=args.gpu, cpu_throttle=throttle,
                graphics_profile=profile, width=args.width, height=args.height,
                output=str(run_dir),
            )
            print(f"[low-end] profile={profile} cpu={throttle:g}x")
            run(bench_args)
            summary = json.loads((run_dir / "results_summary.json").read_text(encoding="utf-8"))
            enforce = profile == "low" and throttle == args.baseline_throttle
            status, failures = verdict(summary, enforce)
            summary["verdict"] = status
            summary["failures"] = failures
            rows.append(summary)
            failed = failed or status == "fail"
            write_report(output, rows)

    print(f"[low-end] report: {output / 'summary.md'}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
