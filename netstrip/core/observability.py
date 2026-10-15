"""
Structured Logging & OpenTelemetry for Cripple-NetStrip
Provides JSON-structured logs, OTLP export, and trace correlation.
"""

import os
import sys
import inspect
import logging
import structlog
from structlog.types import EventDict, WrappedLogger
from typing import Any, Optional
import threading

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace import SpanKind, Status, StatusCode

from netstrip import __version__

# ──────────────────────────────────────────────
#  Configuration
# ──────────────────────────────────────────────

_OTEL_INITIALIZED = False
_OTEL_LOCK = threading.Lock()
_LOGGER_CACHE = {}
_LOGGER_LOCK = threading.Lock()

# Default OTLP endpoint (can be overridden via env)
OTLP_ENDPOINT = os.getenv("CRIPPLE_OTEL_ENDPOINT", "http://localhost:4318/v1/traces")
SERVICE_NAME = "cripple-netstrip"


# ──────────────────────────────────────────────
#  Structlog Processors
# ──────────────────────────────────────────────

def add_service_info(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add service metadata to every log entry."""
    event_dict["service"] = SERVICE_NAME
    event_dict["version"] = __version__
    return event_dict


def add_trace_context(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add current trace/span IDs for correlation."""
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id:
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, '032x')
        event_dict["span_id"] = format(ctx.span_id, '016x')
    return event_dict


def add_severity_level(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Map structlog level to severity."""
    level_map = {
        "debug": "DEBUG",
        "info": "INFO",
        "warning": "WARN",
        "error": "ERROR",
        "critical": "CRITICAL",
    }
    event_dict["severity"] = level_map.get(method_name, "INFO")
    return event_dict


def filter_sensitive_data(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Remove sensitive fields from logs."""
    sensitive_keys = {"password", "token", "api_key", "secret", "psk", "authorization", "cookie"}
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            event_dict[key] = "[REDACTED]"
    return event_dict


# ──────────────────────────────────────────────
#  OpenTelemetry Setup
# ──────────────────────────────────────────────

def init_otel(
    endpoint: str = OTLP_ENDPOINT,
    service_name: str = SERVICE_NAME,
    enable_console: bool = False,
) -> bool:
    """Initialize OpenTelemetry tracer provider with OTLP HTTP exporter."""
    global _OTEL_INITIALIZED
    
    with _OTEL_LOCK:
        if _OTEL_INITIALIZED:
            return True
            
        try:
            # Create resource with service info
            resource = Resource.create({
                SERVICE_NAME: service_name,
                SERVICE_VERSION: __version__,
                "deployment.environment": os.getenv("CRIPPLE_ENV", "production"),
            })
            
            # Create tracer provider
            provider = TracerProvider(resource=resource)
            
            # Add OTLP HTTP exporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=endpoint,
                timeout=10,
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            
            # Optional: console exporter for debugging
            if enable_console or os.getenv("CRIPPLE_OTEL_CONSOLE") == "1":
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            
            # Set global tracer provider
            trace.set_tracer_provider(provider)
            
            # Instrument logging to add trace context
            LoggingInstrumentor().instrument(set_logging_format=True)
            
            _OTEL_INITIALIZED = True
            return True
            
        except Exception as e:
            # Fail silently - logging still works without OTel
            print(f"[OTel] Initialization failed: {e}", file=sys.stderr)
            return False


def get_tracer(name: str = SERVICE_NAME):
    """Get a tracer instance."""
    return trace.get_tracer_provider().get_tracer(name, __version__)


# ──────────────────────────────────────────────
#  Structlog Configuration
# ──────────────────────────────────────────────

def configure_structlog(
    json_output: bool = True,
    log_level: str = "INFO",
) -> None:
    """Configure structlog with JSON output and OpenTelemetry integration."""
    
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_service_info,
        add_trace_context,
        add_severity_level,
        filter_sensitive_data,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_output:
        processors = shared_processors + [structlog.processors.JSONRenderer()]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set stdlib logging level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


# ──────────────────────────────────────────────
#  Logger Factory
# ──────────────────────────────────────────────

def get_logger(name: str = "") -> structlog.BoundLogger:
    """Get a cached structlog logger instance."""
    cache_key = name or "root"
    
    with _LOGGER_LOCK:
        if cache_key not in _LOGGER_CACHE:
            logger = structlog.get_logger(cache_key)
            _LOGGER_CACHE[cache_key] = logger
        return _LOGGER_CACHE[cache_key]


# ──────────────────────────────────────────────
#  Convenience Functions
# ──────────────────────────────────────────────

def log_connection_event(
    logger: structlog.BoundLogger,
    event: str,
    process_name: str,
    domain: str,
    category: str,
    action: str,
    **kwargs,
) -> None:
    """Log a connection event with structured fields."""
    level = "info" if action == "allow" else "warning"
    getattr(logger, level)(
        event,
        process_name=process_name,
        domain=domain,
        category=category,
        action=action,
        **kwargs,
    )


def log_threat_event(
    logger: structlog.BoundLogger,
    threat_type: str,
    message: str,
    severity: str = "high",
    **kwargs,
) -> None:
    """Log a threat/anomaly event."""
    level = "error" if severity in ("high", "critical") else "warning"
    getattr(logger, level)(
        message,
        threat_type=threat_type,
        severity=severity,
        **kwargs,
    )


def log_mode_change(
    logger: structlog.BoundLogger,
    old_mode: str,
    new_mode: str,
    trigger: str = "manual",
    **kwargs,
) -> None:
    """Log a protection mode change."""
    logger.info(
        "Protection mode changed",
        old_mode=old_mode,
        new_mode=new_mode,
        trigger=trigger,
        **kwargs,
    )


# ──────────────────────────────────────────────
#  Context Managers for Tracing
# ──────────────────────────────────────────────

class TraceContext:
    """Context manager for creating traced spans."""
    
    def __init__(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[dict] = None,
        tracer_name: str = SERVICE_NAME,
    ):
        self.name = name
        self.kind = kind
        self.attributes = attributes or {}
        self.tracer = get_tracer(tracer_name)
        self.span = None
        self.token = None
    
    def __enter__(self):
        self.span = self.tracer.start_span(self.name, kind=self.kind)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        # Activate the span for downstream trace.get_current_span() usage.
        use_span_cm = trace.use_span(self.span, end_on_exit=True)
        self.token = use_span_cm.__enter__()
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                self.span.record_exception(exc_val)
            else:
                self.span.set_status(Status(StatusCode.OK))
        finally:
            self.token.__exit__(exc_type, exc_val, exc_tb)
        return False


def traced(name: str, kind: SpanKind = SpanKind.INTERNAL, **attributes):
    """Decorator for tracing sync and coroutine function calls."""
    def decorator(func):
        if inspect.iscoroutinefunction(func):
            async def wrapper(*args, **kwargs):
                with TraceContext(name, kind, attributes) as span:
                    span.set_attribute("function", func.__name__)
                    return await func(*args, **kwargs)
            wrapper.__name__ = func.__name__
            wrapper.__doc__ = func.__doc__
            wrapper.__wrapped__ = func
            return wrapper
        def wrapper(*args, **kwargs):
            with TraceContext(name, kind, attributes) as span:
                span.set_attribute("function", func.__name__)
                return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__wrapped__ = func
        return wrapper
    return decorator