"""
Structured logging module with trace ID propagation for the Finance Copilot system.
Provides JSON-formatted logs with correlation IDs for better front-backend tracing.
"""
import logging
import json
import sys
from datetime import datetime
from uuid import uuid4
import traceback
from typing import Dict, Any, Optional
from contextvars import ContextVar

# Context variable for trace ID propagation
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add trace ID if available
        trace_id = trace_id_var.get()
        if trace_id:
            log_entry['trace_id'] = trace_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'value': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if they exist in the record
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info'):
                log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)


def configure_logging():
    """
    Configure structured logging for the application
    """
    # Configure root logger with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Configure uvicorn loggers to use JSON format
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.addHandler(handler)
    uvicorn_access_logger.setLevel(logging.INFO)
    
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.addHandler(handler)
    uvicorn_error_logger.setLevel(logging.INFO)
    
    return root_logger


def get_trace_id_from_headers(headers: Dict[str, str]) -> str:
    """
    Extract trace ID from request headers, with fallback generation
    """
    # Try to get existing trace ID from header
    trace_id = headers.get('x-trace-id') or headers.get('X-Trace-Id') or headers.get('x-traceid')
    
    if not trace_id:
        # Generate new trace ID if none provided
        trace_id = f"trace-{uuid4().hex[:8]}"
    
    return trace_id


def set_current_trace_id(trace_id: str):
    """
    Set the current trace ID in the context
    """
    trace_id_var.set(trace_id)


def get_current_trace_id() -> Optional[str]:
    """
    Get the current trace ID from the context
    """
    return trace_id_var.get()