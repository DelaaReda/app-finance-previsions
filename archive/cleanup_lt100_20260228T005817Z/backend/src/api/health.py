# src/api/health.py
from __future__ import annotations
from fastapi import APIRouter
from datetime import datetime
from core.config import CONFIG

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "ok",
        "ts": datetime.utcnow().isoformat() + "Z",
        "env": CONFIG.ENV,
        "allow_internet": CONFIG.ALLOW_INTERNET,
        "default_universe": CONFIG.DEFAULT_UNIVERSE,
    }