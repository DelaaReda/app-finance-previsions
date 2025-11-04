import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.response import Response


class FinanceMiddleware(BaseHTTPMiddleware):
    """
    Finance-specific middleware that adds execution time header
    """
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        response.headers["X-Exec-Time-ms"] = str(int((time.time()-start)*1000))
        return response