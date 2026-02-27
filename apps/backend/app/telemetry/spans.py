from __future__ import annotations

from contextlib import contextmanager


@contextmanager
def span(name: str, **attrs):  # noqa: ANN003
    # Lightweight placeholder context manager for custom spans.
    # Replace/extend with direct OpenTelemetry tracer usage as instrumentation matures.
    _ = (name, attrs)
    yield

