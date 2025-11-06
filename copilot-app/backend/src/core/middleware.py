import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Import trace ID functionality
from ..logging.structured_log import trace_id_var


class FinanceMiddleware(BaseHTTPMiddleware):
    """
    Finance-specific middleware that adds execution time and trace ID headers
    """
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        
        # Extract or create trace ID from request headers
        trace_id = self._extract_trace_id_from_request(request)
        
        # Set trace ID in context for structured logging
        token = trace_id_var.set(trace_id)
        
        # Process the request
        response = await call_next(request)
        
        # Add execution time header
        response.headers["X-Exec-Time-ms"] = str(int((time.time() - start) * 1000))
        
        # Add trace ID to response headers to enable front-backend correlation
        response.headers["X-Trace-Id"] = trace_id
        
        # Reset trace ID context
        trace_id_var.reset(token)
        
        return response
    
    def _extract_trace_id_from_request(self, request: Request) -> str:
        """
        Extract trace ID from request headers, or generate a new one if not present
        """
        # Check for trace ID in various possible header formats
        header_keys = ['x-trace-id', 'X-Trace-Id', 'x-traceid', 'trace-id', 'Trace-Id']
        trace_id = None
        
        for key in header_keys:
            if key in request.headers:
                trace_id = request.headers.get(key)
                if trace_id:
                    break
        
        # If no trace ID found in headers, generate a new one
        if not trace_id:
            trace_id = f"trace-{uuid.uuid4().hex[:16]}"  # Use 16 chars for shorter trace IDs
        
        return trace_id
