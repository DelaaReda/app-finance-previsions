from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    data_base: Path = Path(os.getenv("AF_DATA_BASE", "data"))
    cache_ttl_seconds: int = int(os.getenv("AF_CACHE_TTL_SECONDS", "60"))


def get_config() -> AppConfig:
    return AppConfig()

