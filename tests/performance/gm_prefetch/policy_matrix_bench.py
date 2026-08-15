from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


POLICIES = ("simple", "exponential", "sigmoid", "sigmoid_derivative", "utility_per_byte")


def wait_ready(url: str, process: subprocess.Popen[bytes]) -> None:
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError("benchmark server exited before becoming ready")
        try:
            with urllib.request.urlopen(f"{url}/login", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.25)
    raise TimeoutError("benchmark server did not become ready")


def is_dominated(point: dict, points: list[dict]) -> bool:
    return any(
        other is not point
        and other["reveal_p95_ms"] <= point["reveal_p95_ms"]
        and other["wasted_bytes"] <= point["wasted_bytes"]
        and (other["reveal_p95_ms"] < point["reveal_p95_ms"] or other["wasted_bytes"] < point["wasted_bytes"])
        for other in points
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="A-F Andromeda policy matrix (1 GM + 5 players)")
    parser.add_argument("--port", type=int, default=8007)
    parser.add_argument("--output", default="tests/performance/gm_prefetch/results/policy-matrix")
    parser.add_argument("--fixtures", default="tests/performance/gm_prefetch/fixtures.json")
    parser.add_argument("--source-chunk", type=int, default=1)
    parser.add_argument("--target-chunk", type=int, default=2)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    output = root / args.output
    output.mkdir(parents=True, exist_ok=True)
    host = f"http://localhost:{args.port}"
    points: list[dict] = []
    for policy in POLICIES:
        env = os.environ.copy()
        env.update({"GM_HINT_POLICY": policy, "ALLOWED_HOSTS": "*", "WS_ALLOWED_ORIGINS": host})
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(args.port)],
            cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            wait_ready(host, server)
            policy_output = output / policy
            subprocess.run(
                [sys.executable, str(Path(__file__).with_name("andromeda_six_client_bench.py")),
                 "--host", host, "--output", str(policy_output), "--policy", policy,
                 "--fixtures", str(root / args.fixtures),
                 "--source-chunk", str(args.source_chunk), "--target-chunk", str(args.target_chunk)],
                # The same seeded scene and identities are reused for every policy.
                cwd=root, check=True,
            )
            result = json.loads((policy_output / "results_summary.json").read_text(encoding="utf-8"))
            metrics = result["gm_guided"]["metrics"]
            prefetched = sum(item["gm_hint_bytes_prefetched"] for item in metrics)
            promoted = sum(item["gm_hint_bytes_promoted"] for item in metrics)
            points.append({
                "policy": policy,
                "reveal_p50_ms": result["gm_guided"]["reveal_p50_ms"],
                "reveal_p95_ms": result["gm_guided"]["reveal_p95_ms"],
                "critical_requests": sum(result["gm_guided"]["tile_requests_during_reveal"]),
                "prefetched_bytes": prefetched,
                "promoted_bytes": promoted,
                "wasted_bytes": max(0, prefetched - promoted),
                "useful_byte_ratio": promoted / prefetched if prefetched else 0,
                "scheduler_debt_ms": max(item["gm_hint_scheduler_debt_ms"] for item in metrics),
            })
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
    for point in points:
        point["pareto"] = not is_dominated(point, points)
    payload = {"control": "no_gm_prefetch", "clients": {"gm": 1, "players": 5}, "policies": points}
    (output / "matrix_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
