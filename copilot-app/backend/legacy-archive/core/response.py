from fastapi.responses import JSONResponse

def ok(data):
    return {"ok": True, "data": data}

def err(code:int, message:str):
    return JSONResponse({"ok": False, "error": {"code": code, "message": message}}, status_code=code)