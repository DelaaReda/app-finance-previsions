# src/core/config.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import List

def _flag(name: str, default: str = "0") -> bool:
    val = (os.getenv(name, default) or "").strip().lower()
    return val not in ("", "0", "false", "no")

def _list(name: str, default: str = "") -> List[str]:
    raw = os.getenv(name, default) or ""
    return [x.strip() for x in raw.split(",") if x.strip()]

@dataclass(frozen=True)
class AppConfig:
    ENV: str = os.getenv("AF_ENV", "dev")
    ALLOW_INTERNET: bool = _flag("AF_ALLOW_INTERNET", "0")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    DEFAULT_UNIVERSE: tuple = ("SPY", "QQQ", "AAPL", "NVDA", "MSFT")
    NEWS_REGIONS: tuple = ("US", "CA", "INTL")
    DATA_DIR: str = os.getenv("AF_DATA_DIR", "data")
    RAG_TOPK: int = int(os.getenv("AF_RAG_TOPK", "8"))
    API_CORS_ORIGINS: List[str] = _list("AF_API_CORS_ORIGINS", "*")
    RATE_LIMIT_PER_MIN: int = int(os.getenv("AF_RATE_LIMIT_PER_MIN", "120"))

CONFIG = AppConfig()
