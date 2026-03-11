from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS", "300") or "300")
)
_GLOBAL_SIGNAL_MESH_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}

_FREE_SOURCE_REGISTRY: Tuple[Dict[str, Any], ...] = (
    {
        "source_id": "SRC-WORLDBANK",
        "layer": "macro",
        "entity_scope": ["country", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_open_data",
        "license_or_terms_url": "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation",
        "rate_limit_notes": "Public API; keep polling conservative.",
        "freshness_expected": "6h_to_24h",
        "fallback_source_ids": ["SRC-OECD", "SRC-IMF"],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-ECB",
        "layer": "macro",
        "entity_scope": ["country", "continent"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_open_data",
        "license_or_terms_url": "https://data.ecb.europa.eu/help/api/overview",
        "rate_limit_notes": "Public API; use paced refresh.",
        "freshness_expected": "1h_to_6h",
        "fallback_source_ids": ["SRC-EUROSTAT", "SRC-OECD"],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-EUROSTAT",
        "layer": "macro",
        "entity_scope": ["country", "continent"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_open_data",
        "license_or_terms_url": "https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access",
        "rate_limit_notes": "Public API; daily cadence is enough for most datasets.",
        "freshness_expected": "24h",
        "fallback_source_ids": ["SRC-ECB", "SRC-OECD"],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-OECD",
        "layer": "macro",
        "entity_scope": ["country", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_open_data",
        "license_or_terms_url": "https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html",
        "rate_limit_notes": "Public API; monitor quota/rate variability.",
        "freshness_expected": "6h_to_24h",
        "fallback_source_ids": ["SRC-WORLDBANK", "SRC-IMF"],
        "nominal_usage": False,
    },
    {
        "source_id": "SRC-IMF",
        "layer": "macro",
        "entity_scope": ["country", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_open_data",
        "license_or_terms_url": "https://data.imf.org/en/Resource-Pages/IMF-API",
        "rate_limit_notes": "Public API; best used as slower-moving fallback.",
        "freshness_expected": "24h",
        "fallback_source_ids": ["SRC-WORLDBANK", "SRC-OECD"],
        "nominal_usage": False,
    },
    {
        "source_id": "SRC-SEC-EDGAR",
        "layer": "insider",
        "entity_scope": ["company"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api_with_user_agent",
        "license_class": "public_regulatory_data",
        "license_or_terms_url": "https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        "rate_limit_notes": "Respect SEC user-agent guidance and paced requests.",
        "freshness_expected": "1h_to_6h",
        "fallback_source_ids": [],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-GDELT",
        "layer": "geopolitical",
        "entity_scope": ["country", "continent", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_dataset_terms",
        "license_or_terms_url": "https://www.gdeltproject.org/",
        "rate_limit_notes": "Public feed; poll modestly and cache aggressively.",
        "freshness_expected": "15m_to_1h",
        "fallback_source_ids": ["SRC-YAHOO-RSS", "SRC-GOOGLE-NEWS-RSS"],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-UCDP",
        "layer": "geopolitical",
        "entity_scope": ["country", "continent", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_api",
        "license_class": "public_research_data",
        "license_or_terms_url": "https://ucdpapi.pcr.uu.se/",
        "rate_limit_notes": "Low-frequency structured conflict data.",
        "freshness_expected": "24h",
        "fallback_source_ids": ["SRC-GDELT"],
        "nominal_usage": False,
    },
    {
        "source_id": "SRC-EU-PUBLICATIONS-SPARQL",
        "layer": "policy",
        "entity_scope": ["country", "continent"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_query_endpoint",
        "license_class": "public_open_data",
        "license_or_terms_url": "https://op.europa.eu/en/web/about-us/legal-notice",
        "rate_limit_notes": "Use conservative query volume.",
        "freshness_expected": "24h",
        "fallback_source_ids": [],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-STOOQ",
        "layer": "market",
        "entity_scope": ["company", "sector", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_csv",
        "license_class": "public_market_data_terms",
        "license_or_terms_url": "https://stooq.com/",
        "rate_limit_notes": "Public CSV fallback; cache results per symbol batch.",
        "freshness_expected": "15m_to_1h",
        "fallback_source_ids": ["SRC-YAHOO-CHART"],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-YAHOO-CHART",
        "layer": "market",
        "entity_scope": ["company", "sector", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_http",
        "license_class": "public_market_data_terms",
        "license_or_terms_url": "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
        "rate_limit_notes": "Use as fallback with tight caching.",
        "freshness_expected": "15m_to_1h",
        "fallback_source_ids": ["SRC-STOOQ"],
        "nominal_usage": False,
    },
    {
        "source_id": "SRC-YAHOO-RSS",
        "layer": "news",
        "entity_scope": ["company", "sector", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_rss",
        "license_class": "publisher_terms_via_rss",
        "license_or_terms_url": "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
        "rate_limit_notes": "RSS ingestion with per-feed pacing.",
        "freshness_expected": "10m_to_30m",
        "fallback_source_ids": ["SRC-GOOGLE-NEWS-RSS"],
        "nominal_usage": True,
    },
    {
        "source_id": "SRC-GOOGLE-NEWS-RSS",
        "layer": "news",
        "entity_scope": ["company", "sector", "world"],
        "free_tier_status": "NO_KEY",
        "auth_mode": "public_rss",
        "license_class": "publisher_terms_via_rss",
        "license_or_terms_url": "https://policies.google.com/terms",
        "rate_limit_notes": "RSS fallback only; cache by topic/ticker query.",
        "freshness_expected": "10m_to_30m",
        "fallback_source_ids": ["SRC-YAHOO-RSS"],
        "nominal_usage": True,
    },
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _stable_cache_key(include_non_nominal: bool) -> str:
    return f"global_signal_mesh_v1:{int(include_non_nominal)}"


def _cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    if _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS <= 0:
        return None
    entry = _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.get(cache_key)
    if not entry:
        return None
    age_seconds = max(0.0, time.time() - float(entry.get("stored_at") or 0.0))
    if age_seconds > _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS:
        _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.pop(cache_key, None)
        return None
    payload = dict(entry.get("payload") or {})
    payload["cache"] = {
        "hit": True,
        "age_seconds": round(age_seconds, 3),
        "ttl_seconds": _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS,
    }
    return payload


def _cache_set(cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE[cache_key] = {
        "stored_at": time.time(),
        "payload": dict(payload),
    }
    payload["cache"] = {
        "hit": False,
        "age_seconds": 0.0,
        "ttl_seconds": _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS,
    }
    return payload


def _selected_registry(include_non_nominal: bool) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for source in _FREE_SOURCE_REGISTRY:
        if not include_non_nominal and not bool(source.get("nominal_usage")):
            continue
        row = dict(source)
        row["fallback_source_ids"] = list(source.get("fallback_source_ids") or [])
        row["provenance"] = {
            "registry_source": "FREE_DATA_SOURCE_KEY_MATRIX",
            "license_url": row["license_or_terms_url"],
            "nominal_usage": bool(row.get("nominal_usage")),
        }
        rows.append(row)
    return rows


def build_global_signal_mesh_payload(
    *,
    include_non_nominal: bool = False,
    debug: bool = False,
) -> Dict[str, Any]:
    cache_key = _stable_cache_key(include_non_nominal=include_non_nominal)
    if not debug:
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    generated_at = _now_iso()
    sources = _selected_registry(include_non_nominal=include_non_nominal)
    nominal_sources = [item for item in sources if item.get("nominal_usage")]
    layer_counts: Dict[str, int] = {}
    license_counts: Dict[str, int] = {}
    for item in sources:
        layer = str(item.get("layer") or "unknown")
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
        license_class = str(item.get("license_class") or "unknown")
        license_counts[license_class] = license_counts.get(license_class, 0) + 1

    warnings: List[str] = []
    if not nominal_sources:
        warnings.append("no_nominal_free_sources_configured")
    if any(not item.get("fallback_source_ids") for item in nominal_sources):
        warnings.append("some_nominal_sources_have_no_fallback")

    payload = {
        "mesh_id": "free_global_signal_mesh",
        "generated_at": generated_at,
        "freshness": generated_at,
        "last_update": generated_at,
        "source": ["forecasts_global_signal_mesh", "free_data_source_registry"],
        "filters_applied": {
            "include_non_nominal": bool(include_non_nominal),
        },
        "sources_catalog": sources,
        "stats": {
            "source_count": len(sources),
            "nominal_source_count": len(nominal_sources),
            "layer_counts": layer_counts,
            "license_class_counts": license_counts,
        },
        "coverage": {
            "layers": sorted(layer_counts.keys()),
            "nominal_layers": sorted({str(item.get("layer")) for item in nominal_sources}),
            "free_nominal_path_only": True,
        },
        "warnings": warnings,
        "provenance": {
            "source": ["forecasts_global_signal_mesh", "free_data_source_registry"],
            "registry_version": "2026-03-02",
            "registry_backing_doc": "docs/product/planning/FREE_DATA_SOURCE_KEY_MATRIX.md",
            "fallback_used": False,
            "sla": {
                "updated_at": generated_at,
                "freshness_status": "fresh",
                "freshness_age_seconds": 0.0,
                "target_max_age_seconds": _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS,
                "within_target": True,
            },
        },
    }
    if debug:
        payload["cache"] = {
            "hit": False,
            "age_seconds": 0.0,
            "ttl_seconds": _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS,
        }
        payload["debug_pipeline"] = {
            "cache_bypassed": True,
            "selected_sources": [item["source_id"] for item in sources],
        }
        return payload
    return _cache_set(cache_key, payload)
