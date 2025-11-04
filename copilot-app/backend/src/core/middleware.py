"""
Middlewares pour le Finance Copilot API.
Ajoute retry, rate limiting, et logs structurés finance.
"""
import time
import asyncio
from typing import Callable, Awaitable
from functools import wraps
from collections import defaultdict, deque
from datetime import datetime, timedelta
import logging

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

# Rate limiting storage
class RateLimiter:
    def __init__(self, max_calls: int = 100, time_window: int = 60):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> bool:
        now = time.time()
        # Remove old calls outside the window
        while self.calls[identifier] and self.calls[identifier][0] <= now - self.time_window:
            self.calls[identifier].popleft()
        
        # Check if under limit
        if len(self.calls[identifier]) < self.max_calls:
            self.calls[identifier].append(now)
            return True
        return False

rate_limiter = RateLimiter(max_calls=100, time_window=60)  # 100 calls per minute per IP

# Retry utility
async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> any:
    """
    Retry function with exponential backoff.
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func() if asyncio.iscoroutinefunction(func) else func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break
            
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            await asyncio.sleep(delay)
    
    raise last_exception

# Finance-specific logging
class FinanceLogger:
    def __init__(self):
        self.log = logging.getLogger("finance_api")
        self.log.setLevel(logging.INFO)
    
    def log_request(self, request: Request, response: Response = None, duration: float = None, error: str = None):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "client_ip": self.get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "duration_ms": round(duration * 1000, 2) if duration else None,
            "status_code": response.status_code if response else None,
            "error": error
        }
        self.log.info("API Request", extra=log_data)
    
    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host

finance_logger = FinanceLogger()

class FinanceMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.finance_logger = finance_logger
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self.finance_logger.get_client_ip(request)
        
        # Rate limiting
        if not rate_limiter.is_allowed(client_ip):
            self.finance_logger.log_request(
                request, 
                Response(status_code=429), 
                time.time() - start_time,
                "Rate limit exceeded"
            )
            return JSONResponse(
                status_code=429,
                content={"ok": False, "error": "Rate limit exceeded"}
            )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            self.finance_logger.log_request(request, None, duration, str(e))
            raise
        
        duration = time.time() - start_time
        self.finance_logger.log_request(request, response, duration)
        
        return response

def retry_anti_fail(max_retries: int = 3):
    """Decorator for retry logic on external API calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries
            )
        return wrapper
    return decorator