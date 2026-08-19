"""OpenTelemetry span tracing configuration for enterprise APM backends."""

from __future__ import annotations

import os
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
except ImportError:
    trace = None


def setup_otel(service_name: str = "supportmaster") -> Any:
    """Initialize OpenTelemetry tracer provider if available."""
    if trace is None:
        return None
        
    resource = Resource.create(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)
    
    processor = SimpleSpanProcessor(ConsoleSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
