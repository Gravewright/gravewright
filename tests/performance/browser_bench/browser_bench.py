#!/usr/bin/env python3
"""
Real-browser performance benchmark for the live map.

Unlike the WebSocket drivers (which hammer the gateway with synthetic clients),
this drives an actual Chromium tab through the real UI and measures what a player
on a modest laptop would feel:

    * time to map visible   — navigation -> first fully-painted viewport
    * browser memory         — JS heap (performance.memory) + whole browser
                               process-tree RSS (renderer + GPU + main)
    * FPS / stutter          — frame cadence + long tasks while panning/zooming
    * sustained footprint     — memory/heap sampled over the whole run

The "map visible" signal is exact, not a guess: the app exposes
``window.GravewrightMap.debugSnapshot()`` which reports manifest load, the set of
loaded chunks, and which visible chunks are still missing. We treat the map as
visible once the manifest is loaded, at least one chunk is painted, and no
visible chunk is outstanding.

To approximate a weaker 8 GB / iGPU machine, pass ``--cpu-throttle N`` (CDP CPU
slowdown multiplier) and/or run headed against the real GPU. The browser process
RSS we report is the number that matters for an 8 GB box.

Run (against a seeded single-room scene):

    uv run --with playwright --with psutil python \
        tests/performance/browser_bench/browser_bench.py \
        --host http://localhost:8007 --time 3
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

try:
    import psutil
except ImportError:  # process-tree RSS is best-effort; JS heap still works.
    psutil = None  # type: ignore[assignment]


FIXTURES_PATH = Path(__file__).resolve().parents[1] / "ws_live" / "fixtures.json"

# JS recorder installed before any app code runs. It keeps a rolling rAF frame
# clock and a long-task observer; both only accumulate while `recording` is on,
# so the warmup/idle phases don't pollute the pan/zoom numbers.
RECORDER_JS = """
(() => {
  window.__bench = { frames: [], longtasks: [], blocking_ms: 0, recording: false };
  let last = performance.now();
  function tick(now) {
    if (window.__bench.recording) window.__bench.frames.push(now - last);
    last = now;
    window.requestAnimationFrame(tick);
  }
  window.requestAnimationFrame(tick);
  try {
    const po = new PerformanceObserver((list) => {
      if (!window.__bench.recording) return;
      for (const e of list.getEntries()) {
        window.__bench.longtasks.push(e.duration);
        window.__bench.blocking_ms += Math.max(0, e.duration - 50);
      }
    });
    po.observe({ entryTypes: ['longtask'] });
  } catch (_) { /* longtask unsupported: frames still capture jank */ }
})();
"""


@dataclass
class Sample:
    t: float
    js_heap_mb: float
    rss_mb: float


@dataclass
class Results:
    # milestones (ms from navigation start)
    nav_to_canvas_ms: float = 0.0
    nav_to_manifest_ms: float = 0.0
    nav_to_first_chunk_ms: float = 0.0
    time_to_map_visible_ms: float = 0.0
    time_to_realtime_ms: float = 0.0
    map_visible: bool = False

    # interaction / frame stats
    pan_zoom_seconds: float = 0.0
    gestures: int = 0
    frames: int = 0
    fps_avg: float = 0.0
    fps_p50: float = 0.0
    fps_p1_low: float = 0.0  # 1st-percentile fps (worst sustained dips)
    frame_ms_p95: float = 0.0
    frame_ms_p99: float = 0.0
    frame_ms_max: float = 0.0
    jank_frame_pct: float = 0.0  # % frames slower than ~2 vsync (33ms)
    long_tasks: int = 0
    total_blocking_ms: float = 0.0

    # memory
    js_heap_idle_mb: float = 0.0
    js_heap_peak_mb: float = 0.0
    rss_idle_mb: float = 0.0
    rss_peak_mb: float = 0.0

    samples: list[Sample] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return float(ordered[idx])


# ---------------------------------------------------------------------------
# Browser process-tree RSS (best effort, OS-level so thread-safe)
# ---------------------------------------------------------------------------

class RssSampler(threading.Thread):
    """Sum RSS across the Chromium process tree matched by the unique
    user-data-dir we launch with. Captures renderer + GPU + main processes,
    which is the real number for an 8 GB machine. Runs in its own thread; it
    only touches psutil/the OS, never Playwright, so it stays safe alongside the
    sync API on the main thread."""

    def __init__(self, marker: str, interval: float) -> None:
        super().__init__(daemon=True)
        self._marker = marker
        self._interval = interval
        self._stop = threading.Event()
        self.latest_mb = 0.0
        self.peak_mb = 0.0
        self.lock = threading.Lock()

    def _sample_mb(self) -> float:
        if psutil is None:
            return 0.0
        total = 0
        for proc in psutil.process_iter(["cmdline"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                if any(self._marker in part for part in cmdline):
                    total += proc.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return total / (1024 * 1024)

    def run(self) -> None:
        while not self._stop.is_set():
            mb = self._sample_mb()
            with self.lock:
                self.latest_mb = mb
                self.peak_mb = max(self.peak_mb, mb)
            self._stop.wait(self._interval)

    def stop(self) -> None:
        self._stop.set()


# ---------------------------------------------------------------------------
# In-page probes
# ---------------------------------------------------------------------------

def js_heap_mb(page: Page) -> float:
    return float(
        page.evaluate(
            "() => (performance.memory ? performance.memory.usedJSHeapSize/1048576 : 0)"
        )
    )


def map_snapshot(page: Page) -> dict[str, Any] | None:
    return page.evaluate(
        "() => (window.GravewrightMap && window.GravewrightMap.debugSnapshot)"
        " ? window.GravewrightMap.debugSnapshot() : null"
    )


def login(page: Page, host: str, email: str, password: str) -> None:
    page.goto(f"{host}/", wait_until="domcontentloaded")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.click('button[type="submit"]')


def wait_for_map_visible(page: Page, host: str, results: Results, timeout_s: float) -> None:
    """Navigate to /game and clock each milestone up to a fully painted map."""
    nav_start = time.monotonic()
    page.goto(f"{host}/game", wait_until="domcontentloaded")

    page.wait_for_selector("[data-map-canvas]", timeout=timeout_s * 1000)
    results.nav_to_canvas_ms = (time.monotonic() - nav_start) * 1000.0

    deadline = nav_start + timeout_s
    first_chunk_clocked = False
    manifest_clocked = False
    realtime_clocked = False

    while time.monotonic() < deadline:
        snap = map_snapshot(page)
        if snap and snap.get("activeCanvas"):
            now_ms = (time.monotonic() - nav_start) * 1000.0
            if not manifest_clocked and snap.get("manifestLoaded"):
                results.nav_to_manifest_ms = now_ms
                manifest_clocked = True
            chunks = snap.get("chunks") or []
            if not first_chunk_clocked and len(chunks) > 0:
                results.nav_to_first_chunk_ms = now_ms
                first_chunk_clocked = True
            if not realtime_clocked and snap.get("realtimeOpen"):
                results.time_to_realtime_ms = now_ms
                realtime_clocked = True
            missing = snap.get("missingVisibleChunks") or []
            if snap.get("manifestLoaded") and len(chunks) > 0 and len(missing) == 0:
                results.time_to_map_visible_ms = now_ms
                results.map_visible = True
                return
        page.wait_for_timeout(50)

    results.errors.append("map did not reach fully-visible state before timeout")


def canvas_box(page: Page) -> dict[str, float]:
    box = page.eval_on_selector(
        "[data-map-canvas]",
        "el => { const r = el.getBoundingClientRect();"
        " return { x: r.x, y: r.y, w: r.width, h: r.height }; }",
    )
    return box


def run_pan_zoom(page: Page, results: Results, duration_s: float) -> None:
    """Drive realistic pan (drag) and zoom (wheel) gestures over the canvas for
    `duration_s`, while the in-page recorder captures frame cadence + long tasks."""
    box = canvas_box(page)
    cx = box["x"] + box["w"] / 2
    cy = box["y"] + box["h"] / 2
    span_x = box["w"] * 0.30
    span_y = box["h"] * 0.30

    # Install the frame/long-task recorder now that the map is up, then arm it.
    # (Injecting here rather than via add_init_script sidesteps the app's CSP and
    # any client-side navigation that would drop a pre-load script.)
    page.evaluate(RECORDER_JS)
    page.evaluate("() => { window.__bench.recording = true; }")

    started = time.monotonic()
    end = started + duration_s
    gestures = 0
    next_heap_sample = started

    while time.monotonic() < end:
        # Pan: press at center, drag out and back in a few steps (each move is a
        # frame the renderer must keep up with).
        page.mouse.move(cx, cy)
        page.mouse.down()
        for i in range(1, 9):
            f = i / 8.0
            page.mouse.move(cx + span_x * math.sin(f * math.pi),
                            cy + span_y * math.cos(f * math.pi), steps=2)
        page.mouse.up()
        gestures += 1

        # Zoom in then out at the cursor (wheel deltas the camera reacts to).
        page.mouse.move(cx, cy)
        for _ in range(6):
            page.mouse.wheel(0, -120)
            page.wait_for_timeout(16)
        for _ in range(6):
            page.mouse.wheel(0, 120)
            page.wait_for_timeout(16)
        gestures += 1

        now = time.monotonic()
        if now >= next_heap_sample:
            heap = js_heap_mb(page)
            with _RSS_REF.lock if _RSS_REF else _DUMMY_LOCK:
                rss = _RSS_REF.latest_mb if _RSS_REF else 0.0
            results.samples.append(Sample(t=round(now - _RUN_START, 2),
                                          js_heap_mb=round(heap, 1),
                                          rss_mb=round(rss, 1)))
            results.js_heap_peak_mb = max(results.js_heap_peak_mb, heap)
            next_heap_sample = now + 1.0

    intervals = page.evaluate("() => window.__bench.frames")
    longtasks = page.evaluate("() => window.__bench.longtasks")
    blocking = page.evaluate("() => window.__bench.blocking_ms")
    page.evaluate("() => { window.__bench.recording = false; }")

    intervals = [float(x) for x in intervals if x and x > 0]
    results.pan_zoom_seconds = round(time.monotonic() - started, 2)
    results.gestures = gestures
    results.frames = len(intervals)
    results.long_tasks = len(longtasks or [])
    results.total_blocking_ms = round(float(blocking or 0), 1)

    if intervals:
        avg = statistics.fmean(intervals)
        results.fps_avg = round(1000.0 / avg, 1) if avg else 0.0
        p50 = percentile(intervals, 50)
        results.fps_p50 = round(1000.0 / p50, 1) if p50 else 0.0
        # 1%-low fps: worst frame times -> lowest sustained fps.
        p99_ms = percentile(intervals, 99)
        results.fps_p1_low = round(1000.0 / p99_ms, 1) if p99_ms else 0.0
        results.frame_ms_p95 = round(percentile(intervals, 95), 1)
        results.frame_ms_p99 = round(p99_ms, 1)
        results.frame_ms_max = round(max(intervals), 1)
        jank = sum(1 for x in intervals if x > 33.0)  # missed >= 1 frame @ 60Hz
        results.jank_frame_pct = round(100.0 * jank / len(intervals), 2)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

_RSS_REF: RssSampler | None = None
_DUMMY_LOCK = threading.Lock()
_RUN_START = 0.0


def run(args: argparse.Namespace) -> Results:
    global _RSS_REF, _RUN_START
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    email = args.email or fixtures.get("email")
    password = args.password or fixtures.get("password")
    if not email or not password:
        raise SystemExit("no credentials: pass --email/--password or seed fixtures.json")

    duration_s = args.time * 60.0 if args.time and args.time > 0 else float(args.duration)
    results = Results()

    # The unique profile dir is our RSS match marker: Playwright passes it to
    # Chromium as --user-data-dir=<...>/.gwbench-<ts>, so every process in the
    # tree carries the marker in its cmdline. (Don't add --user-data-dir to args
    # ourselves — launch_persistent_context owns that flag and rejects a dupe.)
    marker = f"gwbench-{int(time.time())}"
    user_data_dir = output / f".{marker}"

    launch_args = [
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if args.gpu == "off":
        launch_args += ["--disable-gpu"]

    _RUN_START = time.monotonic()
    if psutil is not None:
        _RSS_REF = RssSampler(marker=marker, interval=0.5)
        _RSS_REF.start()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=not args.headed,
            args=launch_args,
            viewport={"width": args.width, "height": args.height},
        )
        page = context.new_page()

        # Approximate a weaker CPU (8 GB / iGPU laptops are usually CPU-bound on
        # the render thread too) via the CDP throttle multiplier.
        if args.cpu_throttle and args.cpu_throttle > 1:
            client = context.new_cdp_session(page)
            client.send("Emulation.setCPUThrottlingRate", {"rate": args.cpu_throttle})

        try:
            login(page, args.host.rstrip("/"), email, password)
            wait_for_map_visible(page, args.host.rstrip("/"), results, args.load_timeout)

            # Settle, then record the idle baseline before any interaction.
            page.wait_for_timeout(2000)
            results.js_heap_idle_mb = round(js_heap_mb(page), 1)
            if _RSS_REF:
                with _RSS_REF.lock:
                    results.rss_idle_mb = round(_RSS_REF.latest_mb, 1)

            if results.map_visible:
                run_pan_zoom(page, results, duration_s)
            else:
                results.errors.append("skipped pan/zoom: map never became visible")

            results.js_heap_peak_mb = round(max(results.js_heap_peak_mb,
                                                results.js_heap_idle_mb), 1)
        except Exception as exc:  # keep partial results on any failure
            results.errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            try:
                page.screenshot(path=str(output / "final_frame.png"))
            except Exception:
                pass
            context.close()

    if _RSS_REF:
        _RSS_REF.stop()
        results.rss_peak_mb = round(_RSS_REF.peak_mb, 1)

    write_outputs(output=output, args=args, results=results, duration_s=duration_s)
    return results


def write_outputs(*, output: Path, args: argparse.Namespace, results: Results,
                  duration_s: float) -> None:
    summary = {
        "host": args.host,
        "headed": args.headed,
        "gpu": args.gpu,
        "cpu_throttle": args.cpu_throttle,
        "viewport": {"width": args.width, "height": args.height},
        "run_seconds": duration_s,
        "map_visible": results.map_visible,
        "milestones_ms": {
            "nav_to_canvas": round(results.nav_to_canvas_ms, 1),
            "nav_to_manifest": round(results.nav_to_manifest_ms, 1),
            "nav_to_first_chunk": round(results.nav_to_first_chunk_ms, 1),
            "time_to_map_visible": round(results.time_to_map_visible_ms, 1),
            "time_to_realtime": round(results.time_to_realtime_ms, 1),
        },
        "interaction": {
            "pan_zoom_seconds": results.pan_zoom_seconds,
            "gestures": results.gestures,
            "frames": results.frames,
            "fps_avg": results.fps_avg,
            "fps_p50": results.fps_p50,
            "fps_1pct_low": results.fps_p1_low,
            "frame_ms_p95": results.frame_ms_p95,
            "frame_ms_p99": results.frame_ms_p99,
            "frame_ms_max": results.frame_ms_max,
            "jank_frame_pct": results.jank_frame_pct,
            "long_tasks": results.long_tasks,
            "total_blocking_ms": results.total_blocking_ms,
        },
        "memory_mb": {
            "js_heap_idle": results.js_heap_idle_mb,
            "js_heap_peak": results.js_heap_peak_mb,
            "browser_rss_idle": results.rss_idle_mb,
            "browser_rss_peak": results.rss_peak_mb,
            "rss_available": psutil is not None,
        },
        "errors": results.errors,
    }
    (output / "results_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (output / "samples.csv").open("w", encoding="utf-8") as f:
        f.write("elapsed_seconds,js_heap_mb,browser_rss_mb\n")
        for s in results.samples:
            f.write(f"{s.t},{s.js_heap_mb},{s.rss_mb}\n")

    with (output / "summary.md").open("w", encoding="utf-8") as f:
        f.write("# Browser Benchmark — real Chromium on the live map\n\n")
        f.write("## Run\n\n```txt\n")
        f.write(f"host:           {args.host}\n")
        f.write(f"viewport:       {args.width}x{args.height}\n")
        f.write(f"headed:         {args.headed}   gpu: {args.gpu}   cpu_throttle: {args.cpu_throttle}x\n")
        f.write(f"run_seconds:    {duration_s:.0f}\n")
        f.write(f"map_visible:    {results.map_visible}\n")
        f.write("```\n\n")

        f.write("## Time to map visible (ms from navigation)\n\n```txt\n")
        f.write(f"nav -> canvas mounted:   {results.nav_to_canvas_ms:8.0f}\n")
        f.write(f"nav -> manifest loaded:  {results.nav_to_manifest_ms:8.0f}\n")
        f.write(f"nav -> first chunk:      {results.nav_to_first_chunk_ms:8.0f}\n")
        f.write(f"nav -> realtime open:    {results.time_to_realtime_ms:8.0f}\n")
        f.write(f"nav -> MAP VISIBLE:      {results.time_to_map_visible_ms:8.0f}\n")
        f.write("```\n\n")

        f.write("## FPS / stutter during pan + zoom\n\n```txt\n")
        f.write(f"duration:           {results.pan_zoom_seconds:.0f}s   gestures: {results.gestures}\n")
        f.write(f"frames captured:    {results.frames}\n")
        f.write(f"fps avg:            {results.fps_avg}\n")
        f.write(f"fps p50:            {results.fps_p50}\n")
        f.write(f"fps 1% low:         {results.fps_p1_low}\n")
        f.write(f"frame ms p95/p99:   {results.frame_ms_p95} / {results.frame_ms_p99}\n")
        f.write(f"worst frame ms:     {results.frame_ms_max}\n")
        f.write(f"janky frames >33ms: {results.jank_frame_pct}%\n")
        f.write(f"long tasks:         {results.long_tasks}   total blocking: {results.total_blocking_ms} ms\n")
        f.write("```\n\n")

        f.write("## Memory (8 GB machine budget)\n\n```txt\n")
        f.write(f"JS heap idle / peak:       {results.js_heap_idle_mb} / {results.js_heap_peak_mb} MB\n")
        if psutil is not None:
            f.write(f"browser RSS idle / peak:   {results.rss_idle_mb} / {results.rss_peak_mb} MB\n")
        else:
            f.write("browser RSS:               (psutil not installed — JS heap only)\n")
        f.write("```\n")
        if results.errors:
            f.write("\n## Errors\n\n```txt\n")
            for e in results.errors:
                f.write(e + "\n")
            f.write("```\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8007")
    parser.add_argument("--email", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--fixtures", default=str(FIXTURES_PATH))
    parser.add_argument("--time", type=float, default=0.0, help="run time in MINUTES (overrides --duration)")
    parser.add_argument("--duration", type=int, default=120, help="pan/zoom seconds if --time unset")
    parser.add_argument("--load-timeout", type=float, default=60.0, help="seconds to wait for map visible")
    parser.add_argument("--headed", action="store_true", help="show the browser (real GPU on a desktop)")
    parser.add_argument("--gpu", choices=["on", "off"], default="on")
    parser.add_argument("--cpu-throttle", type=float, default=1.0, help="CDP CPU slowdown multiplier (e.g. 4 ~ weaker laptop)")
    parser.add_argument("--width", type=int, default=1366)
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--output", default="tests/performance/browser_bench/results")
    args = parser.parse_args()

    results = run(args)

    print("[browser-bench] Done")
    print(f"  map visible:        {results.map_visible} ({results.time_to_map_visible_ms:.0f} ms)")
    print(f"  fps avg / 1% low:   {results.fps_avg} / {results.fps_p1_low}")
    print(f"  janky frames:       {results.jank_frame_pct}%")
    print(f"  JS heap peak:       {results.js_heap_peak_mb} MB")
    print(f"  browser RSS peak:   {results.rss_peak_mb} MB")
    if results.errors:
        print("  errors:")
        for e in results.errors:
            print(f"    - {e}")


if __name__ == "__main__":
    main()
