# src/api/errors.py
from __future__ import annotations
from fastapi import Request
from fastapi.responses import JSONResponse

class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400, detail: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}

async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "detail": exc.detail, "path": str(request.url)},
    )

async def generic_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": {"type": exc.__class__.__name__}, "path": str(request.url)},
    )