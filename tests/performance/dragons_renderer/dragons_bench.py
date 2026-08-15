from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

try:
    import psutil
except ImportError:
    psutil = None


FIXTURES = Path("tests/performance/gm_prefetch/fixtures-4601217-adaptive.json")
COUNTS = (1, 10, 25, 50, 100, 150, 250, 500, 1000)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * pct / 100) - 1))]


def login(page: Page, host: str, email: str, password: str) -> None:
    page.goto(f"{host}/login", wait_until="domcontentloaded")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.click('button[type="submit"]')
    page.goto(f"{host}/game", wait_until="domcontentloaded")
    page.wait_for_function("() => window.GravewrightMap?.debugSnapshot?.().renderer?.boardReady", timeout=120_000)


def install_workload(page: Page, total: int, visible: int, unique_assets: int = 1) -> None:
    page.evaluate(
        """([total, visible, uniqueAssets]) => {
            if (window.__dragonBenchStop) cancelAnimationFrame(window.__dragonBenchStop);
            const sources = [];
            for (let index = 0; index < uniqueAssets; index += 1) {
                const canvas = document.createElement('canvas');
                canvas.width = 128; canvas.height = 128;
                sources.push({ url: `benchmark://dragon-${index}`, canvas });
            }
            const mapCanvas = window.GravewrightMap.activeCanvas();
            const scene = window.GravewrightMap.sceneDataFor(mapCanvas);
            const state = window.GravewrightMap.stateFor(mapCanvas);
            const rect = mapCanvas.getBoundingClientRect();
            const s = scene.scaledTileSize;
            const left = (-state.offsetX / state.zoom) / s;
            const top = (-state.offsetY / state.zoom) / s;
            const cols = Math.max(1, Math.ceil(Math.sqrt(visible * rect.width / rect.height)));
            const rows = Math.max(1, Math.ceil(visible / cols));
            const stepX = Math.max(.07, (rect.width / state.zoom / s - 2) / cols);
            const stepY = Math.max(.07, (rect.height / state.zoom / s - 2) / rows);
            const tokens = [];
            for (let i = 0; i < total; i += 1) {
                const on = i < visible;
                tokens.push({
                    token_id: `dragon-${i}`, name: '', disposition: 'hostile', hidden: false,
                    grid_x: on ? left + .5 + (i % cols) * stepX : left + 1000 + (i % 100),
                    grid_y: on ? top + .5 + Math.floor(i / cols) * stepY : top + 1000 + Math.floor(i / 100),
                    width_cells: Math.max(.07, Math.min(.8, stepX * .8, stepY * .8)),
                    height_cells: Math.max(.07, Math.min(.8, stepX * .8, stepY * .8)),
                    asset_url: `benchmark://dragon-${i % uniqueAssets}`,
                    benchmark_animated: true, bars: {},
                });
            }
            window.GravewrightMap.benchmarkSetAnimatedTokens(tokens, sources);
            let raf = 0;
            const animate = (now) => {
                const callbackStarted = performance.now();
                const canvasStarted = performance.now();
                sources.forEach(({canvas}, i) => {
                    const ctx = canvas.getContext('2d');
                    const flap = Math.sin(now / 120 + i);
                    ctx.clearRect(0, 0, 128, 128);
                    ctx.fillStyle = '#17352b'; ctx.beginPath(); ctx.arc(64, 66, 31, 0, Math.PI * 2); ctx.fill();
                    ctx.fillStyle = '#58d68d';
                    ctx.beginPath(); ctx.moveTo(62, 62); ctx.lineTo(8, 28 + flap * 16); ctx.lineTo(45, 78); ctx.fill();
                    ctx.beginPath(); ctx.moveTo(66, 62); ctx.lineTo(120, 28 - flap * 16); ctx.lineTo(83, 78); ctx.fill();
                    ctx.fillStyle = '#e74c3c'; ctx.beginPath(); ctx.arc(64, 48, 13, 0, Math.PI * 2); ctx.fill();
                });
                window.__gravewrightPerfRecord?.("animation_canvas", performance.now() - canvasStarted);
                const redrawStarted = performance.now();
                window.GravewrightMap.redraw();
                window.__gravewrightPerfRecord?.("redraw_total", performance.now() - redrawStarted);
                window.__gravewrightPerfRecord?.("animation_callback", performance.now() - callbackStarted);
                raf = requestAnimationFrame(animate);
                window.__dragonBenchStop = raf;
            };
            raf = requestAnimationFrame(animate);
        }""",
        [total, visible, unique_assets],
    )


def chromium_rss_mb(excluded_pids: set[int]) -> float:
    if psutil is None:
        return 0.0
    total = 0
    for process in psutil.process_iter(["pid", "name"]):
        try:
            if process.info["pid"] not in excluded_pids and "chrom" in (process.info["name"] or "").lower():
                total += process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total / 1048576


def browser_gpu(browser, page: Page) -> dict:
    session = browser.new_browser_cdp_session()
    info = session.send("SystemInfo.getInfo").get("gpu", {})
    devices = info.get("devices", [])
    primary = devices[0] if devices else {}
    webgl = page.evaluate("""() => {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return null;
        const ext = gl.getExtension('WEBGL_debug_renderer_info');
        return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    }""")
    return {
        "device_string": primary.get("deviceString"),
        "driver_vendor": primary.get("driverVendor"),
        "driver_version": primary.get("driverVersion"),
        "webgl_renderer": webgl,
        "hardware_accelerated": bool(webgl and "swiftshader" not in webgl.lower()),
    }


def run(page: Page, *, total: int, visible: int, unique_assets: int, warmup: float, duration: float, excluded_pids: set[int]) -> dict:
    install_workload(page, total, visible, unique_assets)
    page.wait_for_timeout(int(warmup * 1000))
    page.evaluate("window.__dragonMetrics = {frames: [], perf: {}, longtasks: []}; window.__dragonLast = performance.now(); window.__dragonRecording = true")
    page.wait_for_timeout(int(duration * 1000))
    raw = page.evaluate("""() => {
        window.__dragonRecording = false;
        return {
            metrics: window.__dragonMetrics,
            heap: performance.memory ? performance.memory.usedJSHeapSize : 0,
            snapshot: window.GravewrightMap.debugSnapshot().renderer,
        };
    }""")
    frames = raw["metrics"]["frames"]
    perf = raw["metrics"]["perf"]
    callback_p95 = percentile(perf.get("animation_callback", []), 95)
    snap = raw["snapshot"]
    return {
        "total_entities": total, "requested_visible": visible, "unique_assets": unique_assets,
        "frames": len(frames), "frame_ms_average": statistics.mean(frames) if frames else 0,
        "frame_ms_p50": percentile(frames, 50), "frame_ms_p95": percentile(frames, 95),
        "frame_ms_p99": percentile(frames, 99), "js_heap_mb": raw["heap"] / 1048576,
        "animation_callback_ms_p95": callback_p95,
        "unattributed_frame_gap_ms_p95": max(0, percentile(frames, 95) - callback_p95),
        "long_tasks": len(raw["metrics"].get("longtasks", [])),
        "long_task_ms_p95": percentile(raw["metrics"].get("longtasks", []), 95),
        "process_rss_mb": chromium_rss_mb(excluded_pids),
        "renderer": {name: {"average": statistics.mean(values), "p95": percentile(values, 95), "p99": percentile(values, 99)} for name, values in perf.items() if values},
        "resources": snap["animatedEntities"], "spatial": snap["spatialIndex"],
        "logical_gpu_mb": snap["textureCache"]["bytes"] / 1048576,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8007")
    parser.add_argument("--fixtures", default=str(FIXTURES))
    parser.add_argument("--output", default="tests/performance/dragons_renderer/results")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--diagnostic-counts", default="")
    args = parser.parse_args()
    fixture = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    warmup, duration = ((1, 3) if args.quick else (2, 5))
    with sync_playwright() as pw:
        excluded_pids = {item.pid for item in psutil.process_iter()} if psutil else set()
        browser = pw.chromium.launch(headless=not args.headed, args=[
            "--enable-precise-memory-info",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-background-timer-throttling",
        ])
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        page.on("pageerror", lambda error: print(f"PAGE_ERROR: {error}"))
        page.add_init_script("""(() => {
            window.__gravewrightMeasureRender = true;
            window.__dragonMetrics = {frames: [], perf: {}, longtasks: []}; window.__dragonRecording = false;
            let last = performance.now();
            const tick = now => { if (window.__dragonRecording) window.__dragonMetrics.frames.push(now-last); last=now; requestAnimationFrame(tick); };
            requestAnimationFrame(tick);
            window.__gravewrightPerfRecord = (name, value) => {
                if (!window.__dragonRecording) return;
                (window.__dragonMetrics.perf[name] ||= []).push(value);
            };
            try {
                new PerformanceObserver(list => {
                    if (!window.__dragonRecording) return;
                    list.getEntries().forEach(entry => window.__dragonMetrics.longtasks.push(entry.duration));
                }).observe({entryTypes: ['longtask']});
            } catch (_) {}
        })();""")
        login(page, args.host, fixture["gm"]["email"], fixture["password"])
        gpu = browser_gpu(browser, page)
        if args.diagnostic_counts:
            counts = tuple(int(value) for value in args.diagnostic_counts.split(",") if value.strip())
            results = [run(page, total=count, visible=count, unique_assets=1, warmup=10, duration=30, excluded_pids=excluded_pids) for count in counts]
            payload = {"headless": not args.headed, "warmup_seconds": 10, "measurement_seconds": 30, "gpu": gpu, "results": results}
            browser.close()
            filename = "diagnostic-scale-headed.json" if args.headed else "diagnostic-scale-headless.json"
            (output / filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(json.dumps(payload, indent=2))
            return
        if args.diagnose:
            result = run(page, total=100, visible=100, unique_assets=1, warmup=10, duration=30, excluded_pids=excluded_pids)
            browser.close()
            result["headless"] = not args.headed
            result["gpu"] = gpu
            filename = "diagnostic-100-headed.json" if args.headed else "diagnostic-100.json"
            (output / filename).write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            return
        ladder_counts = (1, 100, 1000) if args.quick else COUNTS
        culling_cases = ((200, 200), (5000, 50)) if args.quick else ((200, 200), (1000, 200), (1000, 50), (5000, 50))
        ladder = [run(page, total=n, visible=n, unique_assets=1, warmup=warmup, duration=duration, excluded_pids=excluded_pids) for n in ladder_counts]
        culling = [run(page, total=t, visible=v, unique_assets=1, warmup=warmup, duration=duration, excluded_pids=excluded_pids) for t, v in culling_cases]
        sharing = [run(page, total=100, visible=100, unique_assets=u, warmup=warmup, duration=duration, excluded_pids=excluded_pids) for u in (1, 10, 100)]
        canonical = [run(page, total=100, visible=100, unique_assets=1, warmup=10, duration=30, excluded_pids=excluded_pids) for _ in range(1 if args.quick else 5)]
        install_workload(page, 0, 0, 0); page.wait_for_timeout(2000)
        teardown = page.evaluate("() => window.GravewrightMap.debugSnapshot().renderer")
        page.screenshot(path=str(output / "100-dragons.png"))
        version = browser.version
        browser.close()
    result = {
        "benchmark": "gravewright-100-dragons", "version": 1,
        "environment": {"os": platform.platform(), "browser": "Chromium", "browser_version": version, "viewport": [1366, 768], "device_pixel_ratio": 1, "headless": not args.headed, "gpu": gpu},
        "asset": {"kind": "shared-animated-canvas", "width": 128, "height": 128, "unique_main_run": 1, "webm_decoder_measured": False},
        "ladder": ladder, "culling": culling, "sharing": sharing, "canonical_runs": canonical,
        "teardown": {"resources": teardown["animatedEntities"], "spatial": teardown["spatialIndex"], "logical_gpu_mb": teardown["textureCache"]["bytes"] / 1048576},
    }
    (output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    canon_p95 = statistics.median(item["frame_ms_p95"] for item in canonical)
    (output / "summary.md").write_text(
        "# Gravewright 100 Dragons\n\n"
        f"- Canonical median frame p95: {canon_p95:.2f} ms\n"
        f"- 100 instances / unique assets: {canonical[0]['resources']['uniqueAssets']}\n"
        f"- Shared asset hits: {canonical[0]['resources']['sharedAssetHits']}\n"
        f"- Logical GPU: {canonical[0]['logical_gpu_mb']:.2f} MiB\n"
        f"- 5000 total / 50 visible frame p95: {culling[-1]['frame_ms_p95']:.2f} ms\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
