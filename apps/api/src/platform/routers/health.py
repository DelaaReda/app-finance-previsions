from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import time
from typing import Any, Callable

from fastapi import APIRouter


OkFn = Callable[[dict[str, Any]], dict[str, Any]]
FreshnessFn = Callable[[Any, int], dict[str, Any]]
FrontendConfigFn = Callable[[], dict[str, Any]]


def _load_json_compat(filename: str):
    try:
        backend_root = Path(__file__).resolve().parents[3]
        import sys
        if str(backend_root) not in sys.path:
            sys.path.insert(0, str(backend_root))
        from storage.base import load_json  # type: ignore
        return load_json(filename)
    except Exception:
        try:
            from storage.io import load_json  # type: ignore
            return load_json(filename)
        except Exception:
            return None




def _role_state_dir() -> Path:
    return Path(os.environ.get(
        "FC_ROLE_STATE_DIR", str(Path.home() / ".openclaw/cron/role-state")
    )).expanduser()


def _runtime_rate_limit_snapshot() -> dict[str, Any]:
    state_dir = _role_state_dir()
    cooldowns: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not state_dir.exists() or not state_dir.is_dir():
        return {
            "state_dir": str(state_dir),
            "active_count": 0,
            "cooldowns": [],
            "warnings": ["role-state-directory-missing"],
        }

    now = int(time.time())
    for cache_path in sorted(state_dir.glob("*.rate_limit_gate_cache")):
        if not cache_path.is_file():
            continue
        raw = cache_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not raw:
            warnings.append(f"{cache_path.name}:empty")
            continue
        parts = raw.split("|", 1)
        try:
            until_ts = int(parts[0])
        except ValueError:
            warnings.append(f"{cache_path.name}:invalid_format")
            continue
        remaining = until_ts - now
        payload = {
            "actor": cache_path.stem.replace(".rate_limit_gate_cache", ""),
            "remaining_seconds": max(remaining, 0),
            "expires_at": datetime.fromtimestamp(until_ts, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "reason": (parts[1].strip() if len(parts) > 1 else ""),
            "active": remaining > 0,
        }
        cooldowns.append(payload)

    active_cooldowns = [item for item in cooldowns if item.get("active") is True]
    return {
        "state_dir": str(state_dir),
        "active_count": len(active_cooldowns),
        "cooldowns": cooldowns,
        "active_cooldowns": active_cooldowns,
        "warnings": warnings,
    }

def create_health_router(
    *,
    ok_response: OkFn,
    freshness_payload: FreshnessFn,
    frontend_runtime_config: FrontendConfigFn,
    data_freshness_ttl: dict[str, int],
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/health")
    async def health_check():
        last_updates: dict[str, Any] = {}

        forecasts_data = _load_json_compat("forecasts.json")
        if isinstance(forecasts_data, dict):
            last_updates["forecasts"] = forecasts_data.get("last_update")

        news_data = _load_json_compat("news_feed.json")
        if isinstance(news_data, dict):
            last_updates["news"] = news_data.get("last_update")

        brief_data = _load_json_compat("brief_weekly.json")
        if isinstance(brief_data, dict):
            last_updates["brief_weekly"] = brief_data.get("last_update")

        backtests_data = _load_json_compat("backtests.json")
        if isinstance(backtests_data, dict):
            last_updates["backtests"] = backtests_data.get("last_update")

        runtime_governance = _runtime_rate_limit_snapshot()

        health_payload = {
            "status": "ok",
            "backend_up": True,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": ["api_health"],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "version": "0.1.0",
            "last_updates": last_updates,
            "data_paths": {
                "forecasts": "data/forecasts.json",
                "news": "data/news_feed.json",
                "brief_weekly": "data/brief_weekly.json",
                "backtests": "data/backtests.json",
            },
            "stats": {
                "checked_sources": len(last_updates),
                "runtime_governance_active_cooldowns": runtime_governance.get("active_count", 0),
            },
            "runtime_governance": runtime_governance,
        }

        return ok_response({
            **health_payload,
            "service_status": health_payload["status"],
            "runtime_governance_active": runtime_governance.get("active_count", 0) > 0,
        })

    @router.get("/api/freshness")
    async def data_freshness():
        now = datetime.now(timezone.utc)
        forecasts_data = _load_json_compat("forecasts") or _load_json_compat("forecasts.json")
        news_data = _load_json_compat("news_feed") or _load_json_compat("news_feed.json")
        macro_data = _load_json_compat("macro_series") or _load_json_compat("macro_series.json")
        stocks_data = _load_json_compat("stocks/prices") or _load_json_compat("stocks/prices.json")
        backtests_data = _load_json_compat("backtests") or _load_json_compat("backtests.json")
        weekly_brief_data = _load_json_compat("brief_weekly") or _load_json_compat("brief_weekly.json")

        forecasts_meta = freshness_payload(forecasts_data, data_freshness_ttl["forecasts"], now=now)
        news_meta = freshness_payload(news_data, data_freshness_ttl["news_feed"], now=now)
        macro_meta = freshness_payload(macro_data, data_freshness_ttl["macro_series"], now=now)
        stocks_meta = freshness_payload(stocks_data, data_freshness_ttl["stocks"], now=now)
        backtests_meta = freshness_payload(backtests_data, data_freshness_ttl["backtests"], now=now)
        weekly_brief_meta = freshness_payload(weekly_brief_data, data_freshness_ttl["brief_weekly"], now=now)

        return ok_response({
            "macro_freshness_minutes": macro_meta["age_minutes"],
            "news_freshness_minutes": news_meta["age_minutes"],
            "stocks_freshness_minutes": stocks_meta["age_minutes"],
            "backtests_freshness_minutes": backtests_meta["age_minutes"],
            "last_update": now.isoformat().replace("+00:00", "Z"),
            "targets": {
                "forecasts_minutes": round(data_freshness_ttl["forecasts"] / 60),
                "news_minutes": round(data_freshness_ttl["news_feed"] / 60),
                "stocks_minutes": round(data_freshness_ttl["stocks"] / 60),
                "backtests_hours": round(data_freshness_ttl["backtests"] / 3600),
            },
            "freshness": {
                "forecasts": forecasts_meta,
                "news": news_meta,
                "macro": macro_meta,
                "stocks": stocks_meta,
                "backtests": backtests_meta,
                "weekly_brief": weekly_brief_meta,
            },
            "all_fresh": (
                forecasts_meta["is_fresh"]
                and news_meta["is_fresh"]
                and stocks_meta["is_fresh"]
                and backtests_meta["is_fresh"]
            ),
            "source": ["api_health", "freshness_metrics"],
            "status": "ok",
        })

    @router.get("/api/frontend/config")
    async def frontend_config():
        return ok_response(frontend_runtime_config())

    return router
