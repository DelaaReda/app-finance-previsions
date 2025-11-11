import time
from starlette.middleware.base import BaseHTTPMiddleware

class FinanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        response.headers["X-Exec-Time-ms"] = str(int((time.time()-start)*1000))
        return response