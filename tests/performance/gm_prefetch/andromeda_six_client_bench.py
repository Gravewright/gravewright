from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, sync_playwright


def login(page: Page, host: str, email: str, password: str) -> None:
    page.goto(host, wait_until="domcontentloaded")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.click('button[type="submit"]')
    page.goto(f"{host}/game", wait_until="domcontentloaded")
    page.wait_for_selector("[data-map-canvas]", timeout=120_000)
    page.wait_for_function("window.GravewrightMap?.debugSnapshot()?.manifestLoaded", timeout=120_000)


def move_to_chunk(page: Page, cx: int, cy: int) -> None:
    page.evaluate(
        """([cx, cy]) => {
            const canvas = window.GravewrightMap.activeCanvas();
            const scene = window.GravewrightMap.sceneDataFor(canvas);
            const state = window.GravewrightMap.stateFor(canvas);
            const rect = canvas.getBoundingClientRect();
            const chunkWorld = (scene.scaledRasterTileSize || scene.scaledTileSize) * 16;
            const targetX = Math.min((cx + 0.5) * chunkWorld, cx * chunkWorld + Math.max(1, scene.width - cx * chunkWorld) / 2);
            const targetY = Math.min((cy + 0.5) * chunkWorld, cy * chunkWorld + Math.max(1, scene.height - cy * chunkWorld) / 2);
            state.offsetX = rect.width / 2 - targetX * state.zoom;
            state.offsetY = rect.height / 2 - targetY * state.zoom;
            window.GravewrightMap.scheduleViewportUpdate(canvas, true);
            window.GravewrightMap.redraw();
        }""",
        [cx, cy],
    )


def wait_visible(page: Page, timeout_ms: int = 120_000) -> float:
    started = time.perf_counter()
    page.wait_for_function(
        "() => { const s=window.GravewrightMap?.debugSnapshot?.(); return s?.manifestLoaded && s.chunks?.length && !s.missingVisibleChunks?.length; }",
        timeout=timeout_ms,
    )
    return (time.perf_counter() - started) * 1000


def wait_rendered(page: Page, timeout_ms: int = 120_000) -> float:
    started = time.perf_counter()
    page.wait_for_function(
        "() => (window.GravewrightMap?.debugSnapshot?.().renderer?.visibleTileSprites || 0) >= 4",
        timeout=timeout_ms,
    )
    return (time.perf_counter() - started) * 1000


def phase(browser: Browser, host: str, fixtures: dict[str, Any], *, guided: bool, output: Path, source_chunk: int, target_chunk: int) -> dict[str, Any]:
    contexts = []
    pages: list[Page] = []
    tile_requests = [0] * 6
    try:
        identities = [fixtures["gm"], *fixtures["players"]]
        for index, identity in enumerate(identities):
            context = browser.new_context(viewport={"width": 1366, "height": 768})
            contexts.append(context)
            page = context.new_page()
            page.on("request", lambda request, i=index: tile_requests.__setitem__(i, tile_requests[i] + ("/tiles/" in request.url)))
            login(page, host, identity["email"], fixtures["password"])
            page.evaluate("enabled => document.body.dataset.gmGuidedPrefetch = enabled ? 'true' : 'false'", guided)
            pages.append(page)

        gm, players = pages[0], pages[1:]
        for page in players:
            move_to_chunk(page, source_chunk, 0)
        for page in players:
            wait_visible(page)

        move_to_chunk(gm, target_chunk, 0)
        wait_visible(gm)
        if guided:
            # Fixed evidence/warm-up horizon keeps policies comparable and also
            # permits a policy to correctly choose not to speculate.
            gm.wait_for_timeout(10_000)

        before_reveal_requests = list(tile_requests)

        reveal_ms: list[float | None] = [None] * len(players)
        reveal_started = time.perf_counter()
        for page in players:
            move_to_chunk(page, target_chunk, 0)
        deadline = reveal_started + 120
        while any(value is None for value in reveal_ms) and time.perf_counter() < deadline:
            for index, page in enumerate(players):
                if reveal_ms[index] is not None:
                    continue
                visible = page.evaluate("() => window.GravewrightMap.debugSnapshot().renderer?.visibleTileSprites || 0")
                if visible >= 4:
                    reveal_ms[index] = (time.perf_counter() - reveal_started) * 1000
            time.sleep(.01)
        if any(value is None for value in reveal_ms):
            raise TimeoutError(f"players did not render target viewport: {reveal_ms}")
        measured_reveal_ms = [float(value) for value in reveal_ms if value is not None]
        metrics = [page.evaluate("() => window.GravewrightMap.debugSnapshot().metrics") for page in players]
        after_reveal = [tile_requests[i + 1] - before_reveal_requests[i + 1] for i in range(5)]
        for index, page in enumerate(pages):
            page.screenshot(path=str(output / f"{'guided' if guided else 'baseline'}-client-{index}.png"))
        return {
            "reveal_ms": measured_reveal_ms,
            "reveal_p50_ms": statistics.median(measured_reveal_ms),
            "reveal_p95_ms": sorted(measured_reveal_ms)[max(0, int(len(measured_reveal_ms) * .95) - 1)],
            "tile_requests_during_reveal": after_reveal,
            "metrics": metrics,
        }
    finally:
        for context in contexts:
            context.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8007")
    parser.add_argument("--fixtures", default="tests/performance/gm_prefetch/fixtures.json")
    parser.add_argument("--output", default="tests/performance/gm_prefetch/results")
    parser.add_argument("--policy", default="simple")
    parser.add_argument("--source-chunk", type=int, default=1)
    parser.add_argument("--target-chunk", type=int, default=2)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    fixtures = json.loads(Path(args.fixtures).read_text(encoding="utf-8"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        baseline = phase(browser, args.host, fixtures, guided=False, output=output, source_chunk=args.source_chunk, target_chunk=args.target_chunk)
        guided = phase(browser, args.host, fixtures, guided=True, output=output, source_chunk=args.source_chunk, target_chunk=args.target_chunk)
        browser.close()
    result = {
        "image": fixtures["image"], "clients": {"gm": 1, "players": 5}, "policy": args.policy,
        "baseline": baseline, "gm_guided": guided,
        "improvement_pct_p50": round(100 * (baseline["reveal_p50_ms"] - guided["reveal_p50_ms"]) / baseline["reveal_p50_ms"], 2),
    }
    (output / "results_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "summary.md").write_text(
        "# Andromeda — GM-guided prefetch, 1 GM + 5 players\n\n"
        f"- Baseline reveal p50: {baseline['reveal_p50_ms']:.1f} ms\n"
        f"- GM-guided reveal p50: {guided['reveal_p50_ms']:.1f} ms\n"
        f"- Improvement: {result['improvement_pct_p50']:.2f}%\n"
        f"- Baseline tile requests on reveal: {sum(baseline['tile_requests_during_reveal'])}\n"
        f"- Guided tile requests on reveal: {sum(guided['tile_requests_during_reveal'])}\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
