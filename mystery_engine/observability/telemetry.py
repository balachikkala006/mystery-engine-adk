"""OpenTelemetry tracing setup supporting OTLP, Console, and Cloud Trace exporters."""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from mystery_engine.config import Settings, get_settings

logger = logging.getLogger(__name__)
_TELEMETRY_CONFIGURED = False


def configure_telemetry(
    settings: Settings | None = None,
    *,
    force: bool = False,
) -> TracerProvider:
    """Initialize an OpenTelemetry TracerProvider according to runtime configuration."""
    global _TELEMETRY_CONFIGURED
    cfg = settings or get_settings()

    if _TELEMETRY_CONFIGURED and not force:
        current = trace.get_tracer_provider()
        if isinstance(current, TracerProvider):
            return current

    resource = Resource.create({"service.name": cfg.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter_mode = cfg.otel_exporter.lower()

    if exporter_mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OpenTelemetry configured with ConsoleSpanExporter.")
    elif exporter_mode == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        otlp_exporter = OTLPSpanExporter(endpoint=cfg.otel_otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(
            "OpenTelemetry configured with OTLP HTTP exporter (%s).",
            cfg.otel_otlp_endpoint,
        )
    elif exporter_mode == "cloud_trace":
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter()))
            logger.info("OpenTelemetry configured with Google Cloud Trace exporter.")
        except ImportError:
            logger.warning(
                "opentelemetry-exporter-gcp-trace not installed; falling back to no-op tracing."
            )
    else:
        logger.debug("OpenTelemetry initialized in in-process mode (OTEL_EXPORTER=%s).", exporter_mode)

    trace.set_tracer_provider(provider)
    _TELEMETRY_CONFIGURED = True
    return provider


def get_tracer(name: str = "mystery_engine") -> Any:
    """Return an OpenTelemetry tracer scoped to the given instrumentation name."""
    return trace.get_tracer(name)
