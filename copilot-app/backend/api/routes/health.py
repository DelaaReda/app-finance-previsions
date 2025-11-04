from fastapi import APIRouter
from core.response import ok
from storage.io import last_updates_info

router = APIRouter()

@router.get("/health")
def health():
    return ok({"status": "ok", "last_updates": last_updates_info()})