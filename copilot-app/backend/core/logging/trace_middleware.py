"""
Trace ID Middleware for request correlation in the Finance Copilot system.
Extracts or creates trace IDs from headers and propagates them through the request lifecycle.
"""
import uuid
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from backend.core.logging.structured_log import trace_id_var, set_current_trace_id, get_trace_id_from_headers

logger = logging.getLogger(__name__)

class TraceIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle trace ID propagation throughout the request lifecycle
    """
    
    async def dispatch(self, request: Request, call_next):
        # Extract or create trace ID from request headers
        trace_id = get_trace_id_from_headers(dict(request.headers))
        
        # Set trace ID in context
        token = trace_id_var.set(trace_id)
        
        # Add trace ID to response headers
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        
        # Reset context after request
        trace_id_var.reset(token)
        
        return response