"""Small dependency-free counters, gauges, and histogram observations."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Any

from .contracts import MetricPoint


def _key(name: str, labels: dict[str, str]) -> tuple[str, tuple[tuple[str, str], ...]]:
    return name, tuple(sorted((str(k), str(v)) for k, v in labels.items()))


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._types: dict[tuple[str, tuple[tuple[str, str], ...]], str] = {}
        self._samples: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0, *, labels: dict[str, str] | None = None) -> MetricPoint:
        return self._update(name, value, "counter", labels or {}, additive=True)

    def set_gauge(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> MetricPoint:
        return self._update(name, value, "gauge", labels or {}, additive=False)

    def observe(self, name: str, value: float, *, labels: dict[str, str] | None = None) -> MetricPoint:
        point = self._update(name, value, "histogram", labels or {}, additive=True)
        with self._lock:
            self._samples[_key(name, labels or {})].append(float(value))
        return point

    def snapshot(self) -> list[MetricPoint]:
        with self._lock:
            return [
                MetricPoint(name=name, value=value, metric_type=self._types[key], labels=dict(labels))
                for key, value in self._values.items()
                for name, labels in [key]
            ]

    def histogram_samples(self, name: str, *, labels: dict[str, str] | None = None) -> list[float]:
        with self._lock:
            return list(self._samples.get(_key(name, labels or {}), []))

    def _update(self, name: str, value: float, metric_type: str, labels: dict[str, str], *, additive: bool) -> MetricPoint:
        key = _key(name, labels)
        with self._lock:
            self._types[key] = metric_type
            self._values[key] = self._values[key] + float(value) if additive else float(value)
            current = self._values[key]
        return MetricPoint(name=name, value=current, metric_type=metric_type, labels=labels)
