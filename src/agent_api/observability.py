import os
import sys
from contextlib import contextmanager
from typing import Any, Iterator

from google.genai import types
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, Status, StatusCode


SERVICE_NAME = "mcp-gemini-support-agent"
DEFAULT_OTEL_EXPORTER = "console"

_TRACING_CONFIGURED = False


def tracing_is_enabled() -> bool:
    return os.getenv("OTEL_TRACING_ENABLED", "true").lower() not in {
        "0",
        "false",
        "no",
    }


def get_otel_exporter_name() -> str:
    return os.getenv("OTEL_EXPORTER", DEFAULT_OTEL_EXPORTER).lower()


def setup_tracing() -> None:
    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED or not tracing_is_enabled():
        return

    provider = TracerProvider(
        resource=Resource.create({"service.name": SERVICE_NAME}),
    )
    exporter_name = get_otel_exporter_name()
    if exporter_name == "otlp":
        exporter = OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
        )
    else:
        exporter = ConsoleSpanExporter(out=sys.__stdout__)

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _TRACING_CONFIGURED = True


def get_tracer():
    return trace.get_tracer(SERVICE_NAME)


def set_span_attribute(span: Span, key: str, value: Any) -> None:
    if value is not None:
        span.set_attribute(key, value)


def mark_span_error(span: Span, error: Exception) -> None:
    span.record_exception(error)
    span.set_status(Status(StatusCode.ERROR, f"{type(error).__name__}: {error}"))
    span.set_attribute("error.type", type(error).__name__)


@contextmanager
def agent_chat_span(*, trace_id: str, session_id: str, query: str) -> Iterator[Span]:
    with get_tracer().start_as_current_span(
        "agent.chat",
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        span.set_attribute("app.trace_id", trace_id)
        span.set_attribute("app.session_id", session_id)
        span.set_attribute("app.query_length", len(query))
        try:
            yield span
        except Exception as error:
            mark_span_error(span, error)
            raise


@contextmanager
def tool_call_span(
    function_call: types.FunctionCall,
    *,
    url: str,
    attempt: int,
) -> Iterator[Span]:
    tool_name = function_call.name or "unknown"
    with get_tracer().start_as_current_span(
        "agent.tool_call",
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.url", url)
        span.set_attribute("tool.attempt", attempt)
        span.set_attribute("tool.args_count", len(function_call.args or {}))
        try:
            yield span
        except Exception as error:
            mark_span_error(span, error)
            raise
