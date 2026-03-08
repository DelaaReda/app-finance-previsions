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


def _utc_now_iso(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


INGESTION_SOURCE_OBSERVABILITY = (
    ("forecasts", "forecasts", "forecasts"),
    ("news", "news_feed", "news_feed"),
    ("macro_series", "macro_series", "macro_series"),
    ("stocks", "stocks/prices", "stocks"),
    ("backtests", "backtests", "backtests"),
    ("brief_weekly", "brief_weekly", "brief_weekly"),
    ("brief_daily", "brief_daily", "brief_daily"),
)


def _ingestion_source_status(
    *,
    source_name: str,
    file_key: str,
    ttl_key: str,
    freshness_payload: FreshnessFn,
    data_freshness_ttl: dict[str, int],
    now: datetime,
) -> dict[str, Any]:
    payload = _load_json_compat(file_key)
    if payload is None and not file_key.endswith(".json"):
        payload = _load_json_compat(f"{file_key}.json")

    ttl_seconds = data_freshness_ttl.get(ttl_key, 24 * 3600)
    freshness = freshness_payload(payload, ttl_seconds, now=now)
    status = str(freshness.get("status") or "missing")
    is_fresh = bool(freshness.get("is_fresh"))
    errors: list[str] = []

    if payload is None:
        status = "missing"
        errors.append("payload_missing")
    elif not isinstance(payload, dict):
        errors.append("payload_invalid")
        status = "invalid_payload"
    elif status != "fresh":
        errors.append("payload_stale")

    return {
        "source": source_name,
        "file": file_key,
        "status": status,
        "is_fresh": is_fresh,
        "freshness": freshness,
        "errors": errors,
        "path": f"data/{file_key}.json",
    }


def _build_status_payload(route_source: str) -> dict[str, Any]:
    now_iso = _utc_now_iso()
    data_paths = {
        "forecasts": "data/forecasts.json",
        "news": "data/news_feed.json",
        "brief_weekly": "data/brief_weekly.json",
        "backtests": "data/backtests.json",
    }

    try:
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
        warnings = list(runtime_governance.get("warnings") or [])
        status = "ok"

        return {
            "status": status,
            "backend_up": True,
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": [route_source],
            "timestamp": now_iso,
            "version": "0.1.0",
            "last_updates": last_updates,
            "data_paths": data_paths,
            "filters_applied": {},
            "warnings": warnings,
            "stats": {
                "checked_sources": len(last_updates),
                "runtime_governance_active_cooldowns": runtime_governance.get("active_count", 0),
                "warnings_count": len(warnings),
            },
            "runtime_governance": runtime_governance,
            "service_status": status,
            "runtime_governance_active": runtime_governance.get("active_count", 0) > 0,
        }
    except Exception as exc:
        warnings = ["status_payload_failed"]
        return {
            "status": "degraded",
            "backend_up": True,
            "generated_at": now_iso,
            "freshness": now_iso,
            "last_update": now_iso,
            "source": [route_source, "critical_error_fallback"],
            "timestamp": now_iso,
            "version": "0.1.0",
            "last_updates": {},
            "data_paths": data_paths,
            "filters_applied": {},
            "warnings": warnings,
            "stats": {
                "checked_sources": 0,
                "runtime_governance_active_cooldowns": 0,
                "warnings_count": len(warnings),
            },
            "runtime_governance": {
                "state_dir": str(_role_state_dir()),
                "active_count": 0,
                "cooldowns": [],
                "active_cooldowns": [],
                "warnings": warnings,
            },
            "service_status": "degraded",
            "runtime_governance_active": False,
            "error": str(exc),
            "message": "status endpoint fallback (never-empty contract).",
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
        return ok_response(_build_status_payload("api_health"))

    @router.get("/api/status")
    async def status_check():
        return ok_response(_build_status_payload("api_status"))

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

    @router.get("/api/ingestion/health")
    async def ingestion_health():
        now = datetime.now(timezone.utc)
        sources = [
            _ingestion_source_status(
                source_name=source_name,
                file_key=file_key,
                ttl_key=ttl_key,
                freshness_payload=freshness_payload,
                data_freshness_ttl=data_freshness_ttl,
                now=now,
            )
            for source_name, file_key, ttl_key in INGESTION_SOURCE_OBSERVABILITY
        ]

        errors_by_source = {
            item["source"]: item["errors"] for item in sources if item["errors"]
        }
        degraded_count = sum(1 for item in sources if not item["is_fresh"])
        all_fresh = degraded_count == 0

        return ok_response({
            "status": "ok" if all_fresh else "degraded",
            "generated_at": now.isoformat().replace("+00:00", "Z"),
            "source": ["api_health", "ingestion"],
            "sources": sources,
            "degraded_count": degraded_count,
            "errors_by_source": errors_by_source,
            "all_fresh": all_fresh,
        })

    @router.get("/api/frontend/config")
    async def frontend_config():
        return ok_response(frontend_runtime_config())

    return router
