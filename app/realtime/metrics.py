"""In-process counters, gauges and histograms for realtime/HTTP hot paths.

Bounded on both axes, because everything here is fed from request-rate code
paths and the process is long-lived:

* **Samples per histogram**: ``observe`` used to append to an unbounded list
  that was never drained (``snapshot`` only copies, and ``reset`` is never
  called in production). Every WS command, every blocking DB call, every HTTP
  request and every chunk request appended floats that were only released on
  restart. Count/total/min/max are now kept as running scalars (exact, O(1),
  no retention) and only a recent window is retained for the percentile.

* **Distinct series names**: several call sites build a metric name from
  request data, so an unbounded name space is remotely reachable. New names are
  refused past ``MAX_SERIES``; the number refused is reported under the fixed
  ``metrics.series.dropped`` key so the truncation is visible instead of silent.

Both limits are per category and per process. Existing series keep recording
after the cap is hit: only *new* names are refused.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from threading import Lock



MAX_SERIES = 512


MAX_HISTOGRAM_SAMPLES = 2048


@dataclass(frozen=True)
class HistogramSnapshot:
    count: int
    total: float
    min: float
    max: float
    p95: float


@dataclass
class _Histogram:
    """Running aggregates over all observations + a bounded recent window.

    ``count``/``total``/``min``/``max`` cover every observation ever recorded.
    ``samples`` holds only the most recent ``MAX_HISTOGRAM_SAMPLES`` values and
    exists purely so ``p95`` can be computed without retaining full history.
    """

    count: int = 0
    total: float = 0.0
    min: float = math.inf
    max: float = -math.inf
    samples: deque[float] = field(default_factory=lambda: deque(maxlen=MAX_HISTOGRAM_SAMPLES))

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value
        self.samples.append(value)


class RealtimeMetrics:
    def __init__(
        self,
        *,
        max_series: int = MAX_SERIES,
        max_histogram_samples: int = MAX_HISTOGRAM_SAMPLES,
    ) -> None:
        self._lock = Lock()
        self._max_series = max_series
        self._max_histogram_samples = max_histogram_samples
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, _Histogram] = {}
        self._dropped_series = 0

    def _admits(self, store: dict[str, object], name: str) -> bool:
        """Whether ``name`` may be recorded. Caller must hold the lock."""
        if name in store:
            return True
        if len(store) >= self._max_series:
            self._dropped_series += 1
            return False
        return True

    def increment(self, name: str, amount: float = 1) -> None:
        if amount == 0:
            return
        with self._lock:
            if not self._admits(self._counters, name):
                return
            self._counters[name] = self._counters.get(name, 0.0) + amount

    def gauge_add(self, name: str, amount: float) -> None:
        if amount == 0:
            return
        with self._lock:
            if not self._admits(self._gauges, name):
                return
            self._gauges[name] = self._gauges.get(name, 0.0) + amount

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            if not self._admits(self._histograms, name):
                return
            histogram = self._histograms.get(name)
            if histogram is None:
                histogram = _Histogram(samples=deque(maxlen=self._max_histogram_samples))
                self._histograms[name] = histogram
            histogram.observe(value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            counters = dict(self._counters)
            gauges = dict(self._gauges)


            histograms = {
                name: (histogram, list(histogram.samples))
                for name, histogram in self._histograms.items()
                if histogram.count
            }
            dropped = self._dropped_series

        if dropped:
            counters["metrics.series.dropped"] = dropped

        return {
            "counters": counters,
            "gauges": gauges,
            "histograms": {
                name: self._histogram_snapshot(histogram, samples).__dict__
                for name, (histogram, samples) in histograms.items()
            },
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._dropped_series = 0

    @staticmethod
    def _histogram_snapshot(histogram: _Histogram, samples: list[float]) -> HistogramSnapshot:
        ordered = sorted(samples)
        p95_index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
        return HistogramSnapshot(
            count=histogram.count,
            total=histogram.total,
            min=histogram.min,
            max=histogram.max,
            p95=ordered[p95_index] if ordered else 0.0,
        )


realtime_metrics = RealtimeMetrics()
