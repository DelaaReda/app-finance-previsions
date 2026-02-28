from fastapi.responses import JSONResponse

def ok(data):
    """
    Standard success response envelope: { ok: true, data: ... }
    """
    return {"ok": True, "data": data}

def err(code: int, message: str):
    """
    Standard error response: { ok: false, error: { code, message } }
    Returns JSONResponse with appropriate status code
    """
    return JSONResponse(
        {"ok": False, "error": {"code": code, "message": message}}, 
        status_code=code
    )