from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
_RANKED_MODELS_CACHE_TTL_SECONDS = max(
    0.0,
    float(os.getenv("G4F_RANKED_MODELS_CACHE_TTL_SECONDS", "5") or "5"),
)
_RANKED_MODELS_CACHE: Dict[Tuple[str], Dict[str, Any]] = {}

try:
    from g4f.client import Client as G4FClient  # type: ignore
except Exception:
    G4FClient = None

try:
    from core.llm_settings import get_llm_settings
except Exception:  # pragma: no cover
    get_llm_settings = None  # type: ignore


def _backend_root() -> Path:
    # Canonical backend assets live under apps/api/src/platform/legacy/.
    return _src_root() / "platform" / "legacy"


def _src_root() -> Path:
    # apps/api/src/domains/judge/application/g4f_client.py -> parents[3] = apps/api/src
    return Path(__file__).resolve().parents[3]


def _api_root() -> Path:
    return _src_root().parent


def _runtime_llm_models_dir() -> Path:
    return _api_root() / "runtime" / "data" / "llm" / "models"


def _tested_models_path(filename: str) -> Path:
    runtime_path = _runtime_llm_models_dir() / filename
    if runtime_path.is_file():
        return runtime_path
    return _src_root() / filename


def _safe_json_load(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _to_float(value: Any, default: float = 1e9) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _norm_provider(provider: Any) -> Optional[str]:
    text = str(provider or "").strip()
    return text or None


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item and str(item).strip()]


def _is_text_model(model: str) -> bool:
    low = (model or "").strip().lower()
    if not low:
        return False
    blocked = (
        "ocr",
        "vision",
        "image",
        "audio",
        "tts",
        "whisper",
        "embedding",
        "transcribe",
    )
    return not any(token in low for token in blocked)


def _looks_like_auth_wall(answer: Any) -> bool:
    text = str(answer or "").strip().lower()
    if not text:
        return False
    markers = (
        "please log in",
        "sign in",
        "you.com/signin",
        "you.com/pricing",
        "check out our plans",
    )
    return any(marker in text for marker in markers)


def _guess_category(model: str) -> str:
    low = (model or "").lower()
    if any(token in low for token in ("deepseek", "qwen", "llama", "mistral", "gpt-", "o3", "o4", "phi-4", "claude", "pplx")):
        return "forecast"
    if "command-" in low or "json" in low:
        return "helper_json"
    return "basic"


def _model_runtime_priority(model: str) -> int:
    low = (model or "").lower()
    if "qwen-3-235b" in low or "qwen3-235b" in low:
        return 0
    if "qwen" in low:
        return 1
    if "deepseek" in low:
        return 2
    if "phi-4" in low:
        return 3
    if "llama" in low:
        return 4
    return 5


def _model_aliases(model: Optional[str]) -> List[str]:
    raw = str(model or "").strip()
    if not raw:
        return []
    aliases: List[str] = [raw]
    if "/" in raw:
        aliases.append(raw.split("/", 1)[1].strip())
    low = raw.lower()
    if ("qwen3-235b" in low or "qwen-3-235b-a22b" in low) and "qwen-3-235b" not in [a.lower() for a in aliases]:
        aliases.append("qwen-3-235b")
    if "qwen3-235b-a22b" in low and "qwen-3-235b-a22b" not in [a.lower() for a in aliases]:
        aliases.append("qwen-3-235b-a22b")
    if "deepseek/" in low:
        tail = raw.split("/", 1)[1].strip()
        if tail and tail.lower() not in [a.lower() for a in aliases]:
            aliases.append(tail)
    # Deduplicate while preserving order.
    out: List[str] = []
    seen = set()
    for item in aliases:
        k = item.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out


def resolve_llm_mode(mode: Optional[str] = None) -> str:
    """Return normalized LLM execution mode: 'fastest', 'dev', or 'best'."""
    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    default_mode = "best"
    if llm_settings is not None:
        default_mode = getattr(llm_settings, "llm_mode_default", "best") or "best"
    if not str(mode or "").strip():
        fastest_flag = str(os.getenv("LLM_FASTEST_MODE") or "").strip().lower()
        if fastest_flag in {"1", "true", "yes", "on"}:
            return "fastest"
    raw = (
        str(mode or "").strip()
        or str(os.getenv("LLM_MODEL_MODE") or "").strip()
        or str(os.getenv("LLM_EXECUTION_MODE") or "").strip()
        or str(default_mode).strip()
    ).lower()
    if raw in {"fastest", "ultrafast", "speed", "speedrun"}:
        return "fastest"
    if raw in {"dev", "fast", "test", "testing"}:
        return "dev"
    return "best"


def _default_dev_models() -> List[str]:
    return [
        "qwen-3-235b",
        "qwen/qwen3-235b-a22b",
        "deepseek-v3",
        "deepseek/deepseek-v3",
    ]


def _default_fastest_models() -> List[str]:
    # You+gpt-4o-mini = seul provider confirme sans auth (2026-03-03)
    return [
        "gpt-4o-mini",
        "qwen-3-235b",
        "deepseek-v3",
    ]


def _configured_dev_models() -> List[str]:
    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    cfg_models: List[str] = []
    if llm_settings is not None:
        cfg_models = [m for m in (getattr(llm_settings, "llm_dev_models", []) or []) if m]
    env_models = _split_csv(os.getenv("LLM_DEV_MODELS"))
    merged = env_models or cfg_models or _default_dev_models()
    out: List[str] = []
    seen = set()
    for model in merged:
        model_text = str(model or "").strip()
        if not model_text:
            continue
        key = model_text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(model_text)
    return out


def _configured_fastest_models() -> List[str]:
    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    cfg_models: List[str] = []
    if llm_settings is not None:
        cfg_models = [m for m in (getattr(llm_settings, "llm_fastest_models", []) or []) if m]
    env_models = _split_csv(os.getenv("LLM_FASTEST_MODELS"))
    merged = env_models or cfg_models or _default_fastest_models()
    out: List[str] = []
    seen = set()
    for model in merged:
        model_text = str(model or "").strip()
        if not model_text:
            continue
        key = model_text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(model_text)
    return out


def _category_match(model: str, row_category: Optional[str], category_preference: Optional[str]) -> bool:
    wanted = (category_preference or "").strip().lower()
    if not wanted:
        return True
    cat = (row_category or "").strip().lower() or _guess_category(model)
    return cat == wanted


def _working_model_pairs(
    category_preference: Optional[str],
    include_low_confidence: bool = False,
) -> List[Tuple[Optional[str], str]]:
    path = _backend_root() / "data" / "llm" / "models" / "working.json"
    payload = _safe_json_load(path)
    rows = payload.get("models", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return []

    prepared_ok: List[Dict[str, Any]] = []
    prepared_fallback_quality: List[Dict[str, Any]] = []
    prepared_any: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model") or "").strip()
        if not model or not _is_text_model(model):
            continue
        if not _category_match(model, None, category_preference):
            continue
        prepared_row = {
            "provider": _norm_provider(row.get("provider")),
            "model": model,
            "ok": bool(row.get("ok")),
            "pass_rate": _to_float(row.get("pass_rate"), default=0.0),
            "latency_s": _to_float(row.get("latency_s"), default=1e9),
            "source_rank": {
                "verified": 0,
                "test_results": 1,
                "working_results": 2,
                "curated": 3,
                "official": 4,
            }.get(str(row.get("source") or "").strip().lower(), 5),
        }
        prepared_any.append(prepared_row)
        has_quality_signal = (
            prepared_row["provider"] is not None
            or row.get("latency_s") is not None
            or row.get("pass_rate") is not None
            or "/" in model
        )
        if has_quality_signal:
            prepared_fallback_quality.append(prepared_row)
        if bool(row.get("ok")):
            prepared_ok.append(prepared_row)

    prepared = prepared_ok or prepared_fallback_quality
    if not prepared and include_low_confidence:
        prepared = prepared_any
    prepared.sort(
        key=lambda r: (
            r.get("source_rank", 9),
            0 if bool(r.get("ok")) else 1,
            _model_runtime_priority(str(r.get("model") or "")) if not bool(r.get("ok")) else 0,
            -float(r.get("pass_rate", 0.0)),
            float(r.get("latency_s", 1e9)),
            str(r.get("model", "")).lower(),
        )
    )
    return [(row.get("provider"), row["model"]) for row in prepared if row.get("model")]


def _working_fast_pairs(
    category_preference: Optional[str],
    include_low_confidence: bool = True,
) -> List[Tuple[Optional[str], str]]:
    path = _backend_root() / "data" / "llm" / "models" / "working.json"
    payload = _safe_json_load(path)
    rows = payload.get("models", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return []

    prepared: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model") or "").strip()
        if not model or not _is_text_model(model):
            continue
        if not _category_match(model, None, category_preference):
            continue
        ok = bool(row.get("ok"))
        if not ok and not include_low_confidence:
            continue
        prepared.append(
            {
                "provider": _norm_provider(row.get("provider")),
                "model": model,
                "ok": ok,
                "latency_s": _to_float(row.get("latency_s"), default=1e9),
                "pass_rate": _to_float(row.get("pass_rate"), default=0.0),
            }
        )
    prepared.sort(
        key=lambda r: (
            0 if bool(r.get("ok")) else 1,
            float(r.get("latency_s", 1e9)),
            -float(r.get("pass_rate", 0.0)),
            str(r.get("model", "")).lower(),
        )
    )
    return [(row.get("provider"), str(row.get("model") or "")) for row in prepared if row.get("model")]


def _categorized_tested_pairs(category_preference: Optional[str]) -> List[Tuple[Optional[str], str]]:
    path = _tested_models_path("tested_g4f_models_categorized.json")
    payload = _safe_json_load(path)
    if not isinstance(payload, dict):
        return []

    wanted = (category_preference or "").strip().lower()
    if wanted:
        rows = payload.get(wanted) or payload.get(category_preference) or []
        rows = rows if isinstance(rows, list) else []
    else:
        rows = []
        for value in payload.values():
            if isinstance(value, list):
                rows.extend(value)

    prepared: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model") or "").strip()
        if not model or not bool(row.get("ok")) or not _is_text_model(model):
            continue
        prepared.append(
            {
                "provider": _norm_provider(row.get("provider")),
                "model": model,
                "ms": _to_float(row.get("ms")),
            }
        )
    prepared.sort(key=lambda r: (float(r.get("ms", 1e9)), str(r.get("model", "")).lower()))
    return [(row.get("provider"), row["model"]) for row in prepared if row.get("model")]


def _flat_tested_pairs(category_preference: Optional[str]) -> List[Tuple[Optional[str], str]]:
    ok_path = _tested_models_path("tested_g4f_models_ok.json")
    full_path = _tested_models_path("tested_g4f_models.json")
    payload = _safe_json_load(ok_path)
    if not isinstance(payload, list):
        payload = _safe_json_load(full_path)
    rows = payload if isinstance(payload, list) else []

    prepared: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model") or "").strip()
        if not model or not _is_text_model(model):
            continue
        if not bool(row.get("ok")):
            continue
        answer = str(row.get("answer") or "").strip()
        if not answer:
            continue
        if not _category_match(model, row.get("category"), category_preference):
            continue
        prepared.append(
            {
                "provider": _norm_provider(row.get("provider")),
                "model": model,
                "ms": _to_float(row.get("ms")),
            }
        )
    prepared.sort(key=lambda r: (float(r.get("ms", 1e9)), str(r.get("model", "")).lower()))
    return [(row.get("provider"), row["model"]) for row in prepared if row.get("model")]


def _path_signature(path: Path) -> Tuple[int, int, int]:
    try:
        stat = path.stat()
        return (1, int(stat.st_mtime_ns), int(stat.st_size))
    except Exception:
        return (0, 0, 0)


def _ranked_models_signature(category_preference: Optional[str]) -> Tuple[Any, ...]:
    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    working_path = _backend_root() / "data" / "llm" / "models" / "working.json"
    categorized_path = _tested_models_path("tested_g4f_models_categorized.json")
    tested_ok_path = _tested_models_path("tested_g4f_models_ok.json")
    tested_full_path = _tested_models_path("tested_g4f_models.json")
    normalized_category = (category_preference or "").strip().lower()
    return (
        normalized_category,
        _path_signature(working_path),
        _path_signature(categorized_path),
        _path_signature(tested_ok_path),
        _path_signature(tested_full_path),
        str(os.getenv("G4F_PROVIDER") or "").strip().lower(),
        str(os.getenv("G4F_MODEL") or "").strip().lower(),
        str(os.getenv("LLM_MODEL") or "").strip().lower(),
        str(os.getenv("LLM_DEFAULT_MODEL") or "").strip().lower(),
        str(getattr(llm_settings, "g4f_provider", "") or "").strip().lower(),
        str(getattr(llm_settings, "g4f_model", "") or "").strip().lower(),
    )


def _build_ranked_tested_models(category_preference: Optional[str] = "forecast") -> List[Tuple[Optional[str], str]]:
    candidates: List[Tuple[Optional[str], str]] = []
    seen = set()

    def _push(provider: Optional[str], model: Optional[str]) -> None:
        if not model:
            return
        mod = str(model).strip()
        if not mod:
            return
        key = ((provider or "").strip().lower(), mod.lower())
        if key in seen:
            return
        seen.add(key)
        candidates.append((_norm_provider(provider), mod))

    for provider, model in _working_model_pairs(category_preference, include_low_confidence=False):
        _push(provider, model)
    for provider, model in _categorized_tested_pairs(category_preference):
        _push(provider, model)
    for provider, model in _flat_tested_pairs(category_preference):
        _push(provider, model)
    for provider, model in _working_model_pairs(category_preference, include_low_confidence=True):
        _push(provider, model)

    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    if llm_settings is not None:
        _push(llm_settings.g4f_provider, llm_settings.g4f_model)
        _push(None, llm_settings.g4f_model)

    _push(os.getenv("G4F_PROVIDER"), os.getenv("G4F_MODEL"))
    _push(None, os.getenv("G4F_MODEL"))
    _push(None, os.getenv("LLM_MODEL"))
    _push(None, os.getenv("LLM_DEFAULT_MODEL"))
    _push(None, "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")
    return candidates


def get_ranked_tested_models(
    category_preference: Optional[str] = "forecast",
    limit: int = 12,
) -> List[Tuple[Optional[str], str]]:
    """Return ranked tested models as (provider, model) pairs.

    Ranking priority:
    1) data/llm/models/working.json (watcher output, refreshed at startup)
    2) runtime/data/llm/models/tested_g4f_models_categorized.json (fallback: src/)
    3) runtime/data/llm/models/tested_g4f_models_ok.json / tested_g4f_models.json (fallback: src/)
    """
    normalized_category = (category_preference or "").strip().lower()
    cache_key = (normalized_category,)
    now = time.time()
    signature = _ranked_models_signature(normalized_category)
    cache_entry = _RANKED_MODELS_CACHE.get(cache_key)
    use_cache = (
        cache_entry is not None
        and cache_entry.get("signature") == signature
        and (
            _RANKED_MODELS_CACHE_TTL_SECONDS <= 0
            or (now - float(cache_entry.get("ts", 0.0))) <= _RANKED_MODELS_CACHE_TTL_SECONDS
        )
    )
    if use_cache:
        candidates = cache_entry.get("candidates") or []
    else:
        candidates = _build_ranked_tested_models(category_preference=normalized_category)
        _RANKED_MODELS_CACHE[cache_key] = {
            "ts": now,
            "signature": signature,
            "candidates": candidates,
        }

    return candidates[: max(1, int(limit or 12))]


def get_mode_model_candidates(
    mode: Optional[str] = None,
    category_preference: Optional[str] = "forecast",
    limit: int = 16,
) -> List[Tuple[Optional[str], str]]:
    """Return ranked model candidates for a runtime mode."""
    normalized_mode = resolve_llm_mode(mode)
    out: List[Tuple[Optional[str], str]] = []
    seen = set()

    def _push(provider: Optional[str], model: Optional[str]) -> None:
        for alias in _model_aliases(model):
            key = ((provider or "").strip().lower(), alias.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append((_norm_provider(provider), alias))

    if normalized_mode == "fastest":
        for model in _configured_fastest_models():
            _push(None, model)
        for provider, model in _working_fast_pairs(
            category_preference=category_preference,
            include_low_confidence=True,
        ):
            _push(provider, model)
        for provider, model in _categorized_tested_pairs(category_preference):
            _push(provider, model)
        for provider, model in _flat_tested_pairs(category_preference):
            _push(provider, model)
        for provider, model in get_ranked_tested_models(
            category_preference=category_preference,
            limit=max(10, int(limit or 16)),
        ):
            _push(provider, model)
    elif normalized_mode == "dev":
        for model in _configured_dev_models():
            _push(None, model)
        for provider, model in get_ranked_tested_models(
            category_preference=category_preference,
            limit=max(10, int(limit or 16)),
        ):
            _push(provider, model)
    else:
        for provider, model in get_ranked_tested_models(
            category_preference=category_preference,
            limit=max(10, int(limit or 16)),
        ):
            _push(provider, model)
    return out[: max(1, int(limit or 16))]


def _mode_timeout_and_attempts(
    mode: str,
    timeout: Optional[int],
    max_attempts: Optional[int],
) -> Tuple[int, int]:
    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    if timeout is not None:
        timeout_s = max(5, int(timeout))
    else:
        if mode == "fastest":
            timeout_default = (
                getattr(llm_settings, "llm_fastest_timeout_seconds", None)
                if llm_settings is not None
                else None
            )
            timeout_s = max(
                5,
                int(
                    os.getenv(
                        "LLM_FASTEST_TIMEOUT_SECONDS",
                        str(timeout_default if timeout_default is not None else 12),
                    )
                    or "12"
                ),
            )
        elif mode == "dev":
            timeout_default = (
                getattr(llm_settings, "llm_dev_timeout_seconds", None)
                if llm_settings is not None
                else None
            )
            timeout_s = max(
                5,
                int(
                    os.getenv(
                        "LLM_DEV_TIMEOUT_SECONDS",
                        str(timeout_default if timeout_default is not None else 20),
                    )
                    or "20"
                ),
            )
        else:
            timeout_default = (
                getattr(llm_settings, "llm_best_timeout_seconds", None)
                if llm_settings is not None
                else None
            )
            timeout_s = max(
                5,
                int(
                    os.getenv(
                        "LLM_BEST_TIMEOUT_SECONDS",
                        str(timeout_default if timeout_default is not None else 60),
                    )
                    or "60"
                ),
            )

    if max_attempts is not None:
        attempts = max(1, int(max_attempts))
    else:
        if mode == "fastest":
            attempts_default = (
                getattr(llm_settings, "llm_fastest_max_attempts", None)
                if llm_settings is not None
                else None
            )
            attempts = max(
                1,
                int(
                    os.getenv(
                        "LLM_FASTEST_MAX_ATTEMPTS",
                        str(attempts_default if attempts_default is not None else 2),
                    )
                    or "2"
                ),
            )
        elif mode == "dev":
            attempts_default = (
                getattr(llm_settings, "llm_dev_max_attempts", None)
                if llm_settings is not None
                else None
            )
            attempts = max(
                1,
                int(
                    os.getenv(
                        "LLM_DEV_MAX_ATTEMPTS",
                        str(attempts_default if attempts_default is not None else 2),
                    )
                    or "2"
                ),
            )
        else:
            attempts_default = (
                getattr(llm_settings, "llm_best_max_attempts", None)
                if llm_settings is not None
                else None
            )
            attempts = max(
                1,
                int(
                    os.getenv(
                        "LLM_BEST_MAX_ATTEMPTS",
                        str(attempts_default if attempts_default is not None else 3),
                    )
                    or "3"
                ),
            )
    return timeout_s, attempts


def _fastest_tested_model(category_preference: Optional[str] = None) -> Optional[Tuple[str, str]]:
    ranked = get_ranked_tested_models(category_preference=category_preference or "forecast", limit=1)
    if not ranked:
        return None
    provider, model = ranked[0]
    return (provider or "", model)


def call_g4f(
    messages: List[Dict[str, Any]],
    model: str = None,
    provider: str = None,
    timeout: int = 60,
    category_preference: Optional[str] = "forecast",
    max_attempts: Optional[int] = None,
    llm_mode: Optional[str] = None,
    candidate_pairs: Optional[List[Tuple[Optional[str], str]]] = None,
) -> Dict[str, Any]:
    """Call g4f using best-tested model first, with ordered fallbacks."""
    if G4FClient is None:
        return {"ok": False, "error": "g4f_not_installed", "answer": ""}

    llm_settings = get_llm_settings() if get_llm_settings is not None else None
    normalized_mode = resolve_llm_mode(llm_mode)
    candidates: List[Tuple[Optional[str], str]] = []
    seen = set()

    def _push(provider_name: Optional[str], model_name: Optional[str]) -> None:
        prov = _norm_provider(provider_name)
        for model_text in _model_aliases(model_name):
            key = ((prov or "").lower(), model_text.lower())
            if key in seen:
                continue
            seen.add(key)
            candidates.append((prov, model_text))

    explicit_model = str(model or "").strip() or None
    explicit_provider = _norm_provider(provider)
    if explicit_model:
        _push(explicit_provider, explicit_model)
        if explicit_provider is not None:
            _push(None, explicit_model)

    mode_candidates = candidate_pairs or get_mode_model_candidates(
        mode=normalized_mode,
        category_preference=category_preference,
        limit=16,
    )
    for ranked_provider, ranked_model in mode_candidates:
        _push(ranked_provider, ranked_model)

    env_model = str(os.getenv("G4F_MODEL") or "").strip() or None
    env_provider = _norm_provider(os.getenv("G4F_PROVIDER"))
    _push(env_provider, env_model)
    if llm_settings is not None:
        _push(llm_settings.g4f_provider, llm_settings.g4f_model)
        _push(None, llm_settings.g4f_model)
        _push(None, llm_settings.llm_model)

    if not candidates:
        return {"ok": False, "error": "g4f_no_model_candidates", "answer": ""}

    client = G4FClient()
    attempts: List[Dict[str, Any]] = []

    _, mode_max_attempts = _mode_timeout_and_attempts(
        normalized_mode,
        timeout=timeout,
        max_attempts=max_attempts,
    )
    max_tries = mode_max_attempts

    # === FAST PATH: You+gpt-4o-mini confirme sans auth 2026-03-03 ===
    # Tente en premier avant tous les autres candidats, silencieusement
    try:
        import g4f as _g4f
        _you = getattr(_g4f.Provider, "You", None)
        if _you is not None:
            _fast_client = G4FClient(provider=_you)
            _fast_resp = _fast_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                timeout=min(timeout, 15),
            )
            _fast_ans = str(
                _fast_resp.choices[0].message.content
                if _fast_resp and hasattr(_fast_resp, "choices") and _fast_resp.choices
                else ""
            ).strip()
            if _fast_ans and not _looks_like_auth_wall(_fast_ans):
                return {
                    "ok": True,
                    "answer": _fast_ans,
                    "model": "gpt-4o-mini",
                    "provider": "You",
                    "provider_raw": "You",
                    "llm_mode": normalized_mode,
                    "attempted": [],
                }
    except Exception:
        pass
    # === END FAST PATH ===

    for candidate_provider, candidate_model in candidates[:max_tries]:
        kwargs: Dict[str, Any] = {
            "model": candidate_model,
            "messages": messages,
            "timeout": timeout,
        }
        if candidate_provider:
            kwargs["provider"] = candidate_provider
        try:
            try:
                response = client.chat.completions.create(**kwargs)
            except TypeError:
                kwargs.pop("provider", None)
                response = client.chat.completions.create(**kwargs)
                candidate_provider = None
            content = (
                response.choices[0].message.content
                if response and hasattr(response, "choices") and response.choices
                else ""
            )
            answer = str(content or "").strip()
            if not answer:
                attempts.append(
                    {
                        "provider": candidate_provider,
                        "model": candidate_model,
                        "error": "empty_response",
                    }
                )
                continue
            if _looks_like_auth_wall(answer):
                attempts.append(
                    {
                        "provider": candidate_provider,
                        "model": candidate_model,
                        "error": "auth_wall_response",
                    }
                )
                continue
            return {
                "ok": True,
                "answer": answer,
                "model": candidate_model,
                "provider": candidate_provider,
                "provider_raw": candidate_provider,
                "llm_mode": normalized_mode,
                "raw": json.loads(response.model_dump_json()) if hasattr(response, "model_dump_json") else response,
                "attempted": attempts,
            }
        except Exception as exc:
            attempts.append(
                {
                    "provider": candidate_provider,
                    "model": candidate_model,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    err_preview = "; ".join(
        f"{a.get('provider') or 'auto'}|{a.get('model')} -> {a.get('error')}"
        for a in attempts[:6]
    )
    return {
        "ok": False,
        "error": f"g4f_all_candidates_failed: {err_preview or 'no_details'}",
        "answer": "",
        "llm_mode": normalized_mode,
        "attempted": attempts,
    }


def call_llm(
    messages: List[Dict[str, Any]],
    *,
    mode: Optional[str] = None,
    category_preference: Optional[str] = "forecast",
    timeout: Optional[int] = None,
    max_attempts: Optional[int] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Canonical LLM call entrypoint for backend modules.

    Modes:
    - fastest: minimal latency chain (tested fast models first)
    - dev: fast models + shorter timeout + fewer attempts
    - best: ranked tested models + full fallback chain
    """
    normalized_mode = resolve_llm_mode(mode)
    timeout_s, attempts = _mode_timeout_and_attempts(
        normalized_mode,
        timeout=timeout,
        max_attempts=max_attempts,
    )
    candidates = get_mode_model_candidates(
        mode=normalized_mode,
        category_preference=category_preference,
        limit=max(10, attempts * 4),
    )
    res = call_g4f(
        messages=messages,
        model=model,
        provider=provider,
        timeout=timeout_s,
        category_preference=category_preference,
        max_attempts=attempts,
        llm_mode=normalized_mode,
        candidate_pairs=candidates,
    )
    if isinstance(res, dict):
        res.setdefault("llm_mode", normalized_mode)
    return res
