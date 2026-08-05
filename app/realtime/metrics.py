from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class HistogramSnapshot:
    count: int
    total: float
    min: float
    max: float
    p95: float


class RealtimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: defaultdict[str, float] = defaultdict(float)
        self._gauges: defaultdict[str, float] = defaultdict(float)
        self._histograms: defaultdict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, amount: float = 1) -> None:
        if amount == 0:
            return
        with self._lock:
            self._counters[name] += amount

    def gauge_add(self, name: str, amount: float) -> None:
        if amount == 0:
            return
        with self._lock:
            self._gauges[name] += amount

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].append(value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)
            histograms = {
                name: self._histogram_snapshot(values)
                for name, values in self._histograms.items()
                if values
            }

        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": {
                name: snapshot.__dict__
                for name, snapshot in histograms.items()
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    @staticmethod
    def _histogram_snapshot(values: list[float]) -> HistogramSnapshot:
        ordered = sorted(values)
        p95_index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
        return HistogramSnapshot(
            count=len(ordered),
            total=sum(ordered),
            min=ordered[0],
            max=ordered[-1],
            p95=ordered[p95_index],
        )


realtime_metrics = RealtimeMetrics()
