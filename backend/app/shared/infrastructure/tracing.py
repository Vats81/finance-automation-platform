from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def configure_tracing(app: FastAPI, service_name: str) -> None:
    """Wires OpenTelemetry with a console exporter for local/dev visibility.

    Phase 2 swaps ConsoleSpanExporter for an OTLP exporter pointed at a
    collector feeding Prometheus/Grafana/whatever backend is chosen — the
    instrumentation call sites here do not change.
    """
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
