from __future__ import annotations

from copy import deepcopy
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from storage.io import load_json

try:
    from domains.judge.application.judge_pipeline import score_news
except Exception:  # pragma: no cover
    score_news = None  # type: ignore

_GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS", "300") or "300")
)
_GLOBAL_SIGNAL_MESH_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("GLOBAL_SIGNAL_MESH_CACHE_MAX_ENTRIES", "16") or "16")
)
_GLOBAL_SIGNAL_MESH_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_POLICY_IMPACT_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("POLICY_IMPACT_CACHE_TTL_SECONDS", "300") or "300")
)
_POLICY_IMPACT_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("POLICY_IMPACT_CACHE_MAX_ENTRIES", "16") or "16")
)
_POLICY_IMPACT_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_MACRO_REGIME_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("MACRO_REGIME_CACHE_TTL_SECONDS", "300") or "300")
)
_MACRO_REGIME_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("MACRO_REGIME_CACHE_MAX_ENTRIES", "16") or "16")
)
_MACRO_REGIME_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}
_INSIDER_BEHAVIOR_CACHE_TTL_SECONDS = max(
    0, int(os.getenv("INSIDER_BEHAVIOR_CACHE_TTL_SECONDS", "300") or "300")
)
_INSIDER_BEHAVIOR_CACHE_MAX_ENTRIES = max(
    1, int(os.getenv("INSIDER_BEHAVIOR_CACHE_MAX_ENTRIES", "16") or "16")
)
_INSIDER_BEHAVIOR_RESPONSE_CACHE: Dict[str, Dict[str, Any]] = {}

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
    payload = deepcopy(entry.get("payload") or {})
    payload["cache"] = {
        "hit": True,
        "age_seconds": round(age_seconds, 3),
        "ttl_seconds": _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS,
    }
    return payload


def _cache_set(cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    while len(_GLOBAL_SIGNAL_MESH_RESPONSE_CACHE) >= _GLOBAL_SIGNAL_MESH_CACHE_MAX_ENTRIES:
        oldest_key = min(
            _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE,
            key=lambda key: float(
                (_GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.get(key) or {}).get("stored_at") or 0.0
            ),
        )
        _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE.pop(oldest_key, None)
    _GLOBAL_SIGNAL_MESH_RESPONSE_CACHE[cache_key] = {
        "stored_at": time.time(),
        "payload": deepcopy(payload),
    }
    payload["cache"] = {
        "hit": False,
        "age_seconds": 0.0,
        "ttl_seconds": _GLOBAL_SIGNAL_MESH_CACHE_TTL_SECONDS,
    }
    return payload


def _macro_cache_key(country: str, continent: str, horizon: str, include_non_nominal: bool) -> str:
    return (
        "macro_regime_hierarchy_v1:"
        f"{country.upper()}:{continent.lower()}:{horizon.lower()}:{int(include_non_nominal)}"
    )


def _macro_cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    if _MACRO_REGIME_CACHE_TTL_SECONDS <= 0:
        return None
    entry = _MACRO_REGIME_RESPONSE_CACHE.get(cache_key)
    if not entry:
        return None
    age_seconds = max(0.0, time.time() - float(entry.get("stored_at") or 0.0))
    if age_seconds > _MACRO_REGIME_CACHE_TTL_SECONDS:
        _MACRO_REGIME_RESPONSE_CACHE.pop(cache_key, None)
        return None
    payload = deepcopy(entry.get("payload") or {})
    payload["cache"] = {
        "hit": True,
        "age_seconds": round(age_seconds, 3),
        "ttl_seconds": _MACRO_REGIME_CACHE_TTL_SECONDS,
    }
    return payload


def _macro_cache_set(cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    while len(_MACRO_REGIME_RESPONSE_CACHE) >= _MACRO_REGIME_CACHE_MAX_ENTRIES:
        oldest_key = min(
            _MACRO_REGIME_RESPONSE_CACHE,
            key=lambda key: float(
                (_MACRO_REGIME_RESPONSE_CACHE.get(key) or {}).get("stored_at") or 0.0
            ),
        )
        _MACRO_REGIME_RESPONSE_CACHE.pop(oldest_key, None)
    _MACRO_REGIME_RESPONSE_CACHE[cache_key] = {
        "stored_at": time.time(),
        "payload": deepcopy(payload),
    }
    payload["cache"] = {
        "hit": False,
        "age_seconds": 0.0,
        "ttl_seconds": _MACRO_REGIME_CACHE_TTL_SECONDS,
    }
    return payload


_POLICY_STATUS_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("adopted", ("adopted", "approved", "signed into law", "final rule", "implemented")),
    ("proposed", ("proposal", "proposed", "draft bill", "consultation", "planned")),
    ("effective", ("effective on", "takes effect", "in force", "entered into force", "effective immediately")),
)

_POLICY_JURISDICTION_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("US", (" united states ", " u.s. ", " us ", " congress ", " sec ", " federal ", " washington ")),
    ("EU", (" european union ", " eu ", " european commission ", " brussels ", " eu parliament ")),
    ("UK", (" united kingdom ", " uk ", " britain ", " westminster ", " parliament ")),
)

_COUNTRY_TO_CONTINENT: Dict[str, str] = {
    "US": "north_america",
    "USA": "north_america",
    "CA": "north_america",
    "CANADA": "north_america",
    "MX": "north_america",
    "UK": "europe",
    "GB": "europe",
    "GERMANY": "europe",
    "DE": "europe",
    "FRANCE": "europe",
    "FR": "europe",
    "ITALY": "europe",
    "IT": "europe",
    "SPAIN": "europe",
    "ES": "europe",
    "CHINA": "asia",
    "CN": "asia",
    "JAPAN": "asia",
    "JP": "asia",
    "INDIA": "asia",
    "IN": "asia",
    "SOUTH KOREA": "asia",
    "KR": "asia",
    "AUSTRALIA": "oceania",
    "AU": "oceania",
    "BRAZIL": "latin_america",
    "BR": "latin_america",
    "SOUTH AFRICA": "africa",
    "ZA": "africa",
}

_BASELINE_REGIMES: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("world", "world"): {
        "regime": "mixed_disinflation",
        "confidence": 0.68,
        "summary": "Global growth is positive but uneven, with disinflation progress offset by policy and geopolitical fragility.",
        "drivers": ["disinflation progress", "selective policy easing", "geopolitical risk"],
        "risks": ["energy shock rebound", "trade fragmentation", "rate-cut repricing"],
        "score": 0.2,
    },
    ("continent", "north_america"): {
        "regime": "resilient_tightening",
        "confidence": 0.69,
        "summary": "North America remains growth-resilient, but tighter financial conditions still cap upside breadth.",
        "drivers": ["consumer resilience", "AI capex", "restrictive real rates"],
        "risks": ["credit tightening", "election-policy volatility"],
        "score": 0.35,
    },
    ("continent", "europe"): {
        "regime": "fragile_recovery",
        "confidence": 0.63,
        "summary": "Europe is stabilizing from a weak base, but energy and fiscal sensitivity keep the regime fragile.",
        "drivers": ["slowing inflation", "ECB policy pivot optionality", "export sensitivity"],
        "risks": ["energy cost rebound", "industrial slowdown"],
        "score": -0.1,
    },
    ("continent", "asia"): {
        "regime": "policy_divergence",
        "confidence": 0.64,
        "summary": "Asia shows mixed growth with export-tech strength offset by uneven domestic recovery and policy divergence.",
        "drivers": ["electronics cycle", "China demand uncertainty", "regional policy divergence"],
        "risks": ["property drag", "trade restrictions"],
        "score": 0.05,
    },
    ("country", "US"): {
        "regime": "soft_landing_bias",
        "confidence": 0.72,
        "summary": "The US remains in a soft-landing regime with solid demand and slower inflation, but rates still constrain breadth.",
        "drivers": ["labor market resilience", "AI investment cycle", "cooling inflation"],
        "risks": ["late-cycle earnings pressure", "policy repricing"],
        "score": 0.45,
    },
    ("country", "CHINA"): {
        "regime": "policy_supported_slowdown",
        "confidence": 0.66,
        "summary": "China remains in a policy-supported slowdown as stimulus offsets property and confidence headwinds only partially.",
        "drivers": ["targeted stimulus", "export manufacturing", "property stabilization attempts"],
        "risks": ["property spillovers", "external demand weakness"],
        "score": -0.25,
    },
    ("country", "GERMANY"): {
        "regime": "industrial_soft_patch",
        "confidence": 0.64,
        "summary": "Germany is in an industrial soft patch with external demand and energy sensitivity limiting the recovery path.",
        "drivers": ["manufacturing cyclicality", "energy sensitivity", "EU policy support"],
        "risks": ["export contraction", "fiscal constraint"],
        "score": -0.2,
    },
}

_POLICY_SECTOR_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("financials", ("bank", "banking", "capital requirements", "lending", "payments", "fintech")),
    ("technology", ("ai", "artificial intelligence", "semiconductor", "data center", "software", "cloud")),
    ("energy", ("oil", "gas", "energy", "lng", "renewable", "electricity")),
    ("healthcare", ("drug", "pharma", "health", "medicare", "medical device", "biotech")),
    ("industrials", ("tariff", "manufacturing", "industrial", "aerospace", "supply chain")),
)

_POLICY_TRIGGER_KEYWORDS = (
    "regulation",
    "regulatory",
    "legislation",
    "policy",
    "bill",
    "law",
    "rule",
    "compliance",
    "antitrust",
    "sanction",
    "tariff",
)


def _policy_cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    if _POLICY_IMPACT_CACHE_TTL_SECONDS <= 0:
        return None
    entry = _POLICY_IMPACT_RESPONSE_CACHE.get(cache_key)
    if not entry:
        return None
    age_seconds = max(0.0, time.time() - float(entry.get("stored_at") or 0.0))
    if age_seconds > _POLICY_IMPACT_CACHE_TTL_SECONDS:
        _POLICY_IMPACT_RESPONSE_CACHE.pop(cache_key, None)
        return None
    payload = deepcopy(entry.get("payload") or {})
    payload["cache"] = {
        "hit": True,
        "age_seconds": round(age_seconds, 3),
        "ttl_seconds": _POLICY_IMPACT_CACHE_TTL_SECONDS,
    }
    return payload


def _policy_cache_set(cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    while len(_POLICY_IMPACT_RESPONSE_CACHE) >= _POLICY_IMPACT_CACHE_MAX_ENTRIES:
        oldest_key = min(
            _POLICY_IMPACT_RESPONSE_CACHE,
            key=lambda key: float(
                (_POLICY_IMPACT_RESPONSE_CACHE.get(key) or {}).get("stored_at") or 0.0
            ),
        )
        _POLICY_IMPACT_RESPONSE_CACHE.pop(oldest_key, None)
    _POLICY_IMPACT_RESPONSE_CACHE[cache_key] = {
        "stored_at": time.time(),
        "payload": deepcopy(payload),
    }
    payload["cache"] = {
        "hit": False,
        "age_seconds": 0.0,
        "ttl_seconds": _POLICY_IMPACT_CACHE_TTL_SECONDS,
    }
    return payload


def _stable_policy_cache_key(jurisdiction: str, status: str, sector: str, limit: int) -> str:
    return f"policy_impact_v1:{jurisdiction}:{status}:{sector}:{limit}"


def _stable_insider_cache_key(tickers: Tuple[str, ...], limit: int) -> str:
    tickers_key = ",".join(tickers) if tickers else "all"
    return f"insider_behavior_v1:{tickers_key}:{limit}"


def _coerce_text(value: Any) -> str:
    return str(value or "").strip()


def _insider_cache_get(cache_key: str) -> Optional[Dict[str, Any]]:
    if _INSIDER_BEHAVIOR_CACHE_TTL_SECONDS <= 0:
        return None
    entry = _INSIDER_BEHAVIOR_RESPONSE_CACHE.get(cache_key)
    if not entry:
        return None
    age_seconds = max(0.0, time.time() - float(entry.get("stored_at") or 0.0))
    if age_seconds > _INSIDER_BEHAVIOR_CACHE_TTL_SECONDS:
        _INSIDER_BEHAVIOR_RESPONSE_CACHE.pop(cache_key, None)
        return None
    payload = deepcopy(entry.get("payload") or {})
    payload["cache"] = {
        "hit": True,
        "age_seconds": round(age_seconds, 3),
        "ttl_seconds": _INSIDER_BEHAVIOR_CACHE_TTL_SECONDS,
    }
    return payload


def _insider_cache_set(cache_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    while len(_INSIDER_BEHAVIOR_RESPONSE_CACHE) >= _INSIDER_BEHAVIOR_CACHE_MAX_ENTRIES:
        oldest_key = min(
            _INSIDER_BEHAVIOR_RESPONSE_CACHE,
            key=lambda key: float(
                (_INSIDER_BEHAVIOR_RESPONSE_CACHE.get(key) or {}).get("stored_at") or 0.0
            ),
        )
        _INSIDER_BEHAVIOR_RESPONSE_CACHE.pop(oldest_key, None)
    _INSIDER_BEHAVIOR_RESPONSE_CACHE[cache_key] = {
        "stored_at": time.time(),
        "payload": deepcopy(payload),
    }
    payload["cache"] = {
        "hit": False,
        "age_seconds": 0.0,
        "ttl_seconds": _INSIDER_BEHAVIOR_CACHE_TTL_SECONDS,
    }
    return payload


def _normalize_ticker_list(raw_tickers: str) -> Tuple[str, ...]:
    out: List[str] = []
    seen = set()
    for item in str(raw_tickers or "").split(","):
        normalized = _coerce_text(item).upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return tuple(out)


def _ownership_rows(snapshot: Any) -> List[Dict[str, Any]]:
    if isinstance(snapshot, dict):
        tickers = snapshot.get("tickers")
        if isinstance(tickers, dict):
            rows = []
            for ticker, payload in tickers.items():
                if not isinstance(payload, dict):
                    continue
                row = dict(payload)
                row.setdefault("ticker", _coerce_text(ticker).upper())
                rows.append(row)
            return rows
        rows = snapshot.get("rows")
        if isinstance(rows, list):
            return [item for item in rows if isinstance(item, dict)]
        if snapshot.get("ticker") or snapshot.get("insiders"):
            return [snapshot]
    if isinstance(snapshot, list):
        return [item for item in snapshot if isinstance(item, dict)]
    return []


def _insider_window_metrics(snapshot: Dict[str, Any], window_key: str) -> Dict[str, int]:
    window = (((snapshot.get("insiders") or {}).get("aggregates") or {}).get(window_key) or {})
    metrics: Dict[str, int] = {}
    for key in ("buys", "sells", "net_trades"):
        try:
            metrics[key] = int(window.get(key) or 0)
        except Exception:
            metrics[key] = 0
    return metrics


def _insider_signal_row(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    ticker = _coerce_text(snapshot.get("ticker")).upper() or "UNKNOWN"
    metrics_30d = _insider_window_metrics(snapshot, "window_30d")
    metrics_90d = _insider_window_metrics(snapshot, "window_90d")
    coverage_windows = sum(
        1 for item in (metrics_30d, metrics_90d) if any(int(item.get(k) or 0) != 0 for k in ("buys", "sells", "net_trades"))
    )
    uncertainty_factors: List[str] = []
    if coverage_windows == 0:
        uncertainty_factors.append("no_recent_form4_activity")
    if coverage_windows == 1:
        uncertainty_factors.append("single_window_signal")
    if metrics_30d["buys"] == metrics_30d["sells"] == 0:
        uncertainty_factors.append("window_30d_sparse")

    net_30d = metrics_30d["net_trades"]
    net_90d = metrics_90d["net_trades"]
    if net_30d > 0 and net_90d >= 0:
        stance = "accumulation_bias"
    elif net_30d < 0 and net_90d <= 0:
        stance = "distribution_bias"
    elif net_30d == 0 and net_90d == 0:
        stance = "insufficient_evidence"
    else:
        stance = "mixed_signal"

    uncertainty_level = "high" if len(uncertainty_factors) >= 2 else "medium" if uncertainty_factors else "low"
    confidence_score = round(max(0.15, min(0.75, 0.3 + (0.15 * coverage_windows) - (0.1 * len(uncertainty_factors)))), 2)
    interpretation = (
        f"Insider activity for {ticker} suggests {stance.replace('_', ' ')} "
        f"but remains non-deterministic and should be combined with other layers."
    )

    return {
        "ticker": ticker,
        "stance": stance,
        "summary": interpretation,
        "confidence": confidence_score,
        "uncertainty": {
            "level": uncertainty_level,
            "factors": uncertainty_factors or ["baseline_caution_required"],
        },
        "activity": {
            "window_30d": metrics_30d,
            "window_90d": metrics_90d,
        },
        "provenance": {
            "source": list(snapshot.get("sources_used") or ["SEC EDGAR"]),
            "asof_utc": _coerce_text(snapshot.get("asof_utc")) or None,
            "filing_source": "public_form4",
        },
        "guardrails": {
            "deterministic_language_allowed": False,
            "standalone_decision_grade": "not_allowed",
            "review_note": "Use insider behavior only as corroborating evidence.",
        },
    }


def _extract_policy_status(text: str) -> str:
    haystack = f" {text.lower()} "
    for label, keywords in _POLICY_STATUS_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "monitoring"


def _extract_jurisdiction(text: str) -> str:
    haystack = f" {text.lower()} "
    for label, keywords in _POLICY_JURISDICTION_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "global"


def _extract_sector_tags(text: str) -> List[str]:
    haystack = text.lower()
    sectors: List[str] = []
    for label, keywords in _POLICY_SECTOR_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            sectors.append(label)
    return sectors or ["broad_market"]


def _extract_effective_date(text: str) -> Optional[str]:
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)
    return None


def _is_policy_article(article: Dict[str, Any]) -> bool:
    text = " ".join(
        _coerce_text(article.get(field))
        for field in ("title", "headline", "summary", "description", "raw_text")
    ).lower()
    return any(keyword in text for keyword in _POLICY_TRIGGER_KEYWORDS)


def build_policy_change_impact_payload(
    *,
    jurisdiction: str = "all",
    status: str = "all",
    sector: str = "all",
    limit: int = 10,
    debug: bool = False,
) -> Dict[str, Any]:
    normalized_jurisdiction = _coerce_text(jurisdiction).upper() or "ALL"
    normalized_status = _coerce_text(status).lower() or "all"
    normalized_sector = _coerce_text(sector).lower() or "all"
    normalized_limit = max(1, min(int(limit), 25))
    cache_key = _stable_policy_cache_key(
        normalized_jurisdiction,
        normalized_status,
        normalized_sector,
        normalized_limit,
    )
    if not debug:
        cached = _policy_cache_get(cache_key)
        if cached is not None:
            return cached

    generated_at = _now_iso()
    snapshot = load_json("news_feed") or {}
    articles = snapshot.get("articles") if isinstance(snapshot, dict) else []
    articles = articles if isinstance(articles, list) else []
    policy_articles = [article for article in articles if isinstance(article, dict) and _is_policy_article(article)]

    ranked_candidates = score_news(policy_articles, cap=max(normalized_limit * 3, normalized_limit)) if callable(score_news) else []
    candidate_by_title = {
        _coerce_text(item.get("title")): item for item in ranked_candidates if _coerce_text(item.get("title"))
    }

    events: List[Dict[str, Any]] = []
    for article in policy_articles:
        title = _coerce_text(article.get("title") or article.get("headline"))
        summary = _coerce_text(article.get("summary") or article.get("description"))
        if not title:
            continue
        body_text = " ".join((title, summary, _coerce_text(article.get("raw_text")))).strip()
        event_jurisdiction = _extract_jurisdiction(body_text)
        event_status = _extract_policy_status(body_text)
        sectors = _extract_sector_tags(body_text)
        companies = list(article.get("tickers") or article.get("symbols") or [])
        if normalized_jurisdiction != "ALL" and event_jurisdiction != normalized_jurisdiction:
            continue
        if normalized_status != "all" and event_status != normalized_status:
            continue
        if normalized_sector != "all" and normalized_sector not in sectors:
            continue
        ranked = candidate_by_title.get(title, {})
        event = {
            "event_id": _coerce_text(article.get("id")) or title.lower().replace(" ", "-")[:80],
            "title": title,
            "summary": summary[:240],
            "jurisdiction": event_jurisdiction,
            "status": event_status,
            "effective_date": _extract_effective_date(body_text),
            "sectors": sectors,
            "companies": companies,
            "impact_score": round(min(1.0, 0.35 + (0.12 * len(sectors)) + (0.08 * len(companies))), 4),
            "evidence": {
                "published_at": _coerce_text(article.get("timestamp") or article.get("published_at") or article.get("date")),
                "source": _coerce_text(article.get("source")) or "news_feed",
                "age_hours": ranked.get("age_hours"),
                "judge_ranked": bool(ranked),
            },
        }
        events.append(event)

    events.sort(
        key=lambda item: (
            float(item.get("impact_score") or 0.0),
            _coerce_text(item.get("evidence", {}).get("published_at")),
        ),
        reverse=True,
    )
    events = events[:normalized_limit]

    status_counts: Dict[str, int] = {}
    jurisdiction_counts: Dict[str, int] = {}
    sector_counts: Dict[str, int] = {}
    for event in events:
        event_status = _coerce_text(event.get("status")) or "monitoring"
        status_counts[event_status] = status_counts.get(event_status, 0) + 1
        event_jurisdiction = _coerce_text(event.get("jurisdiction")) or "global"
        jurisdiction_counts[event_jurisdiction] = jurisdiction_counts.get(event_jurisdiction, 0) + 1
        for item in event.get("sectors") or []:
            item_text = _coerce_text(item)
            if not item_text:
                continue
            sector_counts[item_text] = sector_counts.get(item_text, 0) + 1

    warnings: List[str] = []
    if not policy_articles:
        warnings.append("no_policy_articles_detected")
    elif not events:
        warnings.append("filters_excluded_all_policy_events")

    payload = {
        "engine_id": "policy_change_impact_v1",
        "generated_at": generated_at,
        "freshness": generated_at,
        "last_update": generated_at,
        "source": ["forecasts_policy_change_impact", "news_feed_snapshot", "judge_score_news"],
        "filters_applied": {
            "jurisdiction": normalized_jurisdiction,
            "status": normalized_status,
            "sector": normalized_sector,
            "limit": normalized_limit,
        },
        "events": events,
        "stats": {
            "policy_article_count": len(policy_articles),
            "returned_event_count": len(events),
            "status_counts": status_counts,
            "jurisdiction_counts": jurisdiction_counts,
            "sector_counts": sector_counts,
        },
        "timeline": {
            "effective_now_count": sum(1 for event in events if event.get("status") == "effective"),
            "proposed_count": sum(1 for event in events if event.get("status") == "proposed"),
            "adopted_count": sum(1 for event in events if event.get("status") == "adopted"),
        },
        "warnings": warnings,
        "provenance": {
            "source": ["forecasts_policy_change_impact", "news_feed_snapshot", "judge_score_news"],
            "fallback_used": False,
            "sla": {
                "updated_at": generated_at,
                "freshness_status": "fresh",
                "freshness_age_seconds": 0.0,
                "target_max_age_seconds": _POLICY_IMPACT_CACHE_TTL_SECONDS,
                "within_target": True,
            },
        },
    }
    if debug:
        payload["cache"] = {
            "hit": False,
            "age_seconds": 0.0,
            "ttl_seconds": _POLICY_IMPACT_CACHE_TTL_SECONDS,
        }
        payload["debug_pipeline"] = {
            "cache_bypassed": True,
            "candidate_count": len(policy_articles),
            "ranked_title_count": len(candidate_by_title),
        }
        return payload
    return _policy_cache_set(cache_key, payload)


def build_insider_behavior_payload(
    *,
    tickers: str = "",
    limit: int = 10,
    debug: bool = False,
) -> Dict[str, Any]:
    normalized_tickers = _normalize_ticker_list(tickers)
    normalized_limit = max(1, min(int(limit), 25))
    cache_key = _stable_insider_cache_key(normalized_tickers, normalized_limit)
    if not debug:
        cached = _insider_cache_get(cache_key)
        if cached is not None:
            return cached

    generated_at = _now_iso()
    snapshot = load_json("ownership_snapshot") or {}
    rows = _ownership_rows(snapshot)
    if normalized_tickers:
        rows = [
            item
            for item in rows
            if _coerce_text(item.get("ticker")).upper() in normalized_tickers
        ]

    signals = [_insider_signal_row(item) for item in rows]
    signals.sort(
        key=lambda item: (
            float(item.get("confidence") or 0.0),
            abs(int((((item.get("activity") or {}).get("window_30d") or {}).get("net_trades") or 0))),
        ),
        reverse=True,
    )
    signals = signals[:normalized_limit]

    warnings: List[str] = []
    if not rows:
        warnings.append("no_ownership_snapshot_rows")
    elif not signals:
        warnings.append("filters_excluded_all_insider_rows")

    payload = {
        "engine_id": "insider_behavior_intelligence_v1",
        "generated_at": generated_at,
        "freshness": generated_at,
        "last_update": generated_at,
        "source": ["forecasts_insider_behavior", "ownership_snapshot", "sec_edgar_form4"],
        "filters_applied": {
            "tickers": list(normalized_tickers),
            "limit": normalized_limit,
        },
        "signals": signals,
        "stats": {
            "snapshot_row_count": len(rows),
            "returned_signal_count": len(signals),
            "stance_counts": {
                stance: sum(1 for item in signals if item.get("stance") == stance)
                for stance in ("accumulation_bias", "distribution_bias", "mixed_signal", "insufficient_evidence")
            },
            "high_uncertainty_count": sum(
                1 for item in signals if ((item.get("uncertainty") or {}).get("level") == "high")
            ),
        },
        "guardrails": {
            "deterministic_language_allowed": False,
            "policy": "Insider activity is evidence with uncertainty, never a standalone directive.",
        },
        "warnings": warnings,
        "provenance": {
            "source": ["forecasts_insider_behavior", "ownership_snapshot", "sec_edgar_form4"],
            "fallback_used": False,
            "snapshot_key": "ownership_snapshot",
            "sla": {
                "updated_at": generated_at,
                "freshness_status": "fresh",
                "freshness_age_seconds": 0.0,
                "target_max_age_seconds": _INSIDER_BEHAVIOR_CACHE_TTL_SECONDS,
                "within_target": True,
            },
        },
    }
    if debug:
        payload["cache"] = {
            "hit": False,
            "age_seconds": 0.0,
            "ttl_seconds": _INSIDER_BEHAVIOR_CACHE_TTL_SECONDS,
        }
        payload["debug_pipeline"] = {
            "cache_bypassed": True,
            "snapshot_row_count": len(rows),
            "selected_tickers": [item.get("ticker") for item in signals],
        }
        return payload
    return _insider_cache_set(cache_key, payload)


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
