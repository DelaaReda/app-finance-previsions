"""
G4F Model Watcher — keeps a local working list of high‑quality g4f models.

- Selects SOTA verified models (using src.runners.sanity_runner_ia_chat if network allows)
- Tests a handful with short prompts via g4f, measures latency
- Writes: data/llm/models/working.json

Use:
  python -m src.agents.g4f_model_watcher --refresh --limit 8
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Optional API keys (read from env; do NOT hardcode)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


WORKING_PATH = Path("data/llm/models/working.json")
DEFAULT_REMOTE_URL = os.getenv(
    "G4F_WORKING_URL",
    "https://raw.githubusercontent.com/maruf009sultan/g4f-working/main/working/working_results.txt",
)
DEFAULT_MODELS_TXT_URL = os.getenv(
    "G4F_MODELS_TXT_URL",
    "https://raw.githubusercontent.com/Free-AI-Things/g4f-working/main/working/models.txt",
)
DEFAULT_WORKING_RESULTS_URL = os.getenv(
    "G4F_WORKING_RESULTS_URL",
    "https://raw.githubusercontent.com/Free-AI-Things/g4f-working/main/working/working_results.txt",
)
TEST_RESULTS_JSON_URL = os.getenv(
    "G4F_TEST_RESULTS_URL",
    "https://raw.githubusercontent.com/Free-AI-Things/g4f-working/main/working/test_results.json",
)
SUPPORTED_MODEL_PATTERNS = ()  # accept any model name (broadest set)
BLOCKED_MODEL_PATTERNS = ()    # no hard block; we rely on probe results
MAX_STORED_MODELS = int(os.getenv("G4F_WORKING_MAX_STORED", "64"))
ALLOWED_SHORT_PREFIXES = ()  # allow even bare names from the working list


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ModelProbe:
    model: str
    ok: bool
    provider: Optional[str]
    latency_s: Optional[float]
    pass_rate: Optional[float] = None
    source: Optional[str] = None  # 'verified' | 'official' | 'curated' | None
    error: Optional[str] = None
    endpoint: Optional[str] = None  # URL/provider hint if available
    tested_at: str = _now_iso()


def _ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def _is_supported_model(name: Optional[str]) -> bool:
    # Broad acceptance: any non-empty model string
    return bool(name and str(name).strip())


def _is_premium_model(name: str) -> bool:
    if not name:
        return False
    slug = name.lower()
    premium_sub = (
        "deepseek", "qwen", "qwq", "llama", "mistral", "phi-4",
        "gpt-5", "gpt-4o", "gpt-4.1", "r1", "o3", "o4", "glm", "grok",
    )
    return any(k in slug for k in premium_sub)


# Curated priority list (tiers) for finance/forecast + code/reporting
CURATED_PRIORITY = [
    # Tier S
    "gpt-5-thinking",
    "deepseek-r1-0528",
    "deepseek-v3",
    "deepseek-v3-0324",
    "deepseek-v3-0324-turbo",
    "Qwen/Qwen3-235B-A22B-Thinking-2507",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    # Tier A code/quant
    "Qwen/Qwen3-Coder-30B-A3B-Instruct",
    "Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo",
    "microsoft/phi-4",
    "microsoft/phi-4-reasoning-plus",
    # Fast / cheap
    "gpt-4o-mini",
    "gpt-5-mini",
    "mistralai/Mistral-Small-3.2-24B-Instruct-2506",
    "qwen-3-14b",
    "qwen-3-30b",
    "qwen-3-32b",
    # Reporting
    "claude-opus-4",
    "claude-3.5-sonnet",
    "claude-sonnet-4.5",
    "claude-3.5-haiku",
    "claude-haiku-4.5",
]


def _filter_econ_models(models: List[str], limit: int = 32) -> List[str]:
    """
    Garde les modèles textuels généralistes (finance/raisonnement), évite code/vision/ocr/audio.
    """
    banned_sub = (
        "coder", "code", "dev", "ocr", "vision", "image", "video", "audio", "asr", "whisper",
        "embedding", "tts", "speech", "vl-", "flux", "midjourney", "stable-diffusion",
    )
    keep_sub = (
        "deepseek", "qwen", "glm", "llama", "gpt-oss", "phi", "gemma", "mixtral", "mistral",
        "grok", "o3", "o4", "r1", "claude", "command", "gemini", "opus", "haiku",
        "gpt-5", "gpt-4o", "mistral-small",
    )
    def _rank_curated(m: str) -> int:
        for i, ref in enumerate(CURATED_PRIORITY):
            if m.lower() == ref.lower():
                return i
        return len(CURATED_PRIORITY) + 1
    out = []
    seen = set()
    # 1) inject curated list (even si pas présent dans models.txt)
    for m in CURATED_PRIORITY:
        if m in seen:
            continue
        seen.add(m)
        out.append((m, "curated"))
        if limit and len(out) >= limit:
            break
    # 2) complete with filtered models.txt preserving order
    for m in models:
        if not m:
            continue
        if m in seen:
            continue
        slug = m.strip().lower()
        if any(b in slug for b in banned_sub):
            continue
        if keep_sub and not any(k in slug for k in keep_sub):
            continue
        seen.add(m)
        out.append((m.strip(), "models_txt"))
        if limit and len(out) >= limit:
            break
    # Sort by curated rank, then keep curated first in order
    ordered = []
    for m, src in out:
        ordered.append((m, src, _rank_curated(m)))
    ordered.sort(key=lambda t: t[2])
    if limit:
        ordered = ordered[:limit]
    return ordered


def _provider_for_model(model: str) -> Optional[str]:
    """Best-effort mapping model -> provider id."""
    m = (model or "").lower()
    if "deepseek" in m:
        return "deep-infra"
    if "qwen" in m:
        return "deep-infra"
    if "phi-4" in m:
        return "openrouter"
    if "mistral" in m:
        return "openrouter"
    if "gpt-5" in m or "gpt-4o" in m or m.startswith("o3") or "o4" in m:
        return "openrouter"
    if "claude" in m:
        return "api.airforce"
    return None


def build_working_from_models_txt(url: str = DEFAULT_MODELS_TXT_URL, limit: int = 32) -> Path:
    """
    Charge models.txt (g4f-working), filtre les modèles généralistes (macro/texte) et écrit working.json.
    """
    import urllib.request
    try:
        raw = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", errors="ignore")
        lines = [ln.split("(", 1)[0].strip() for ln in raw.splitlines() if ln.strip()]
        models_with_src = _filter_econ_models(lines, limit=limit)
        probes = []
        for m, src, _rank in models_with_src:
            probes.append(ModelProbe(model=m, ok=True, provider=None, latency_s=None, source=src))
        return _save_working(probes)
    except Exception as e:
        # fallback to static
        probes = [ModelProbe(model=m, ok=False, provider=None, latency_s=None, source="static") for m in _static_candidates()[:limit]]
        return _save_working(probes)


def build_working_from_test_results(url: str = TEST_RESULTS_JSON_URL, limit: int = 32) -> Path:
    """
    Charge working/test_results.json (g4f-working), retient les modèles textuels "working"
    et écrit working.json avec le provider / latence fournis (re-probe léger avec le provider indiqué).
    """
    import urllib.request
    try:
        from runners.sanity_runner_ia_chat import g4f_chat_once
    except Exception:
        g4f_chat_once = None
    try:
        raw = urllib.request.urlopen(url, timeout=10).read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
        items = data.get("working_models") or data.get("models") or []
        models: List[ModelProbe] = []
        premium_sub = ("deepseek", "qwen3", "qwen", "llama-3.3", "llama-4", "phi-4", "mistral", "gpt-4o", "gpt-5", "r1", "o3", "o4")
        for it in items:
            m = it.get("model") or it.get("name") if isinstance(it, dict) else str(it)
            provider = it.get("provider") if isinstance(it, dict) else None
            latency = it.get("response_time") or it.get("latency") or it.get("latency_s") if isinstance(it, dict) else None
            if not m or not _is_supported_model(m):
                continue
            if not any(p in m.lower() for p in premium_sub):
                continue
            ok = True
            err = None
            # re-probe léger si g4f_chat_once est dispo
            if g4f_chat_once:
                try:
                    txt = g4f_chat_once(provider=provider or "auto", prompt="ping", model=m, timeout=15)
                    if not txt:
                        ok = False
                        err = "No response"
                except Exception as e:
                    ok = False
                    err = f"{type(e).__name__}: {e}"
            models.append(ModelProbe(model=m, ok=ok, provider=provider, latency_s=latency, source="test_results", endpoint=provider, error=err))
            if limit and len(models) >= limit:
                break
        if not models:
            models = [ModelProbe(model=m, ok=False, provider=None, latency_s=None, source="static") for m in _static_candidates()[:limit]]
        return _save_working(models)
    except Exception:
        probes = [ModelProbe(model=m, ok=False, provider=None, latency_s=None, source="static") for m in _static_candidates()[:limit]]
        return _save_working(probes)


async def refresh_async(limit: int = 8, refresh_verified: bool = True, concurrency: int = 4, timeout: int = 60) -> Path:
    """
    Version asynchrone de refresh : teste les modèles en parallèle (to_thread) avec timeout allongé (60s).
    """
    source = os.getenv('G4F_SOURCE', 'both').lower().strip()
    cand: List[Dict[str, Any]] = []
    # 0) Inject curated priority first (premium)
    cand.extend([{"model": m, "__source": "curated"} for m in CURATED_PRIORITY])
    # 0bis) Inject working/test_results.json premium subset
    try:
        import urllib.request
        raw = urllib.request.urlopen(TEST_RESULTS_JSON_URL, timeout=10).read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
        items = data.get("working_models") or data.get("models") or []
        for it in items:
            m = it.get("model") if isinstance(it, dict) else str(it)
            if not m or not _is_supported_model(m):
                continue
            premium_sub = ("deepseek", "qwen3", "qwen", "llama-3.3", "llama-4", "phi-4", "mistral", "gpt-4o", "gpt-5", "r1", "o3", "o4")
            if not any(p in m.lower() for p in premium_sub):
                continue
            cand.append({"model": m, "__source": "test_results"})
    except Exception:
        pass
    if source in ('verified', 'both'):
        for it in _verified_candidates(limit=limit, refresh=refresh_verified):
            it = dict(it); it['__source'] = 'verified'; cand.append(it)
    if source in ('official', 'both'):
        for it in _official_candidates(limit=limit):
            it = dict(it); it['__source'] = 'official'; cand.append(it)
    if not cand:
        cand = [{"model": m, "pass_rate": None, "hint": None, "__source": None} for m in _static_candidates()[:limit]]

    seen = set(); merged: List[Dict[str, Any]] = []
    for it in cand:
        m = it.get('model')
        if m and m not in seen:
            seen.add(m); merged.append(it)

    sem = asyncio.Semaphore(concurrency)
    async def _task(c):
        m = c.get("model") if isinstance(c, dict) else str(c)
        if not _is_supported_model(m):
            return None
        pr = ModelProbe(model=m, ok=False, provider=None, latency_s=None, pass_rate=c.get("pass_rate") if isinstance(c, dict) else None, source=c.get("__source"))
        async with sem:
            try:
                provider_id = _provider_for_model(m)
                probe = await _probe_model_async(m, timeout=timeout, provider_id=provider_id)
                probe.source = c.get('__source')
                probe.pass_rate = pr.pass_rate
                if provider_id and not probe.provider:
                    probe.provider = provider_id
                if provider_id and not probe.endpoint:
                    probe.endpoint = provider_id
                return probe
            except Exception:
                return pr

    tasks = [_task(c) for c in merged]
    probes = [p for p in await asyncio.gather(*tasks) if p]
    return _save_working(probes)


def _filter_supported_probes(objs: Iterable[ModelProbe]) -> List[ModelProbe]:
    return [o for o in objs if _is_supported_model(o.model)]


def _rank_probe_for_storage(probe: ModelProbe) -> tuple:
    return (
        not probe.ok,
        probe.latency_s if probe.latency_s is not None else 9999.0,
        -(probe.pass_rate or 0.0),
        (probe.model or "").lower(),
    )


def _load_working() -> Dict[str, Any]:
    try:
        return json.loads(WORKING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"asof": _now_iso(), "models": []}


def _save_working(objs: List[ModelProbe]) -> Path:
    filtered = _filter_supported_probes(objs)
    if not filtered:
        # fallback: keep at least static power list so callers always get something usable
        filtered = [
            ModelProbe(model=m, ok=False, provider=None, latency_s=None)
            for m in _static_candidates() or []
        ]
    # If curated order provided, preserve input order; else sort by probe score
    if not any(getattr(x, "source", None) == "curated" for x in filtered):
        filtered.sort(key=_rank_probe_for_storage)
    if MAX_STORED_MODELS and len(filtered) > MAX_STORED_MODELS:
        filtered = filtered[:MAX_STORED_MODELS]
    payload = {
        "asof": _now_iso(),
        "models": [asdict(x) for x in filtered],
    }
    _ensure_dir(WORKING_PATH)
    WORKING_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return WORKING_PATH


def _static_candidates() -> List[str]:
    # fallback: use static power list from econ_llm_agent
    try:
        from analytics.econ_llm_agent import POWER_NOAUTH_MODELS
        return POWER_NOAUTH_MODELS[:]
    except Exception:
        return []


def _verified_candidates(limit: int = 12, refresh: bool = True) -> List[Dict[str, Any]]:
    # import lazy to avoid hard dependency when network is blocked
    try:
        from runners.sanity_runner_ia_chat import select_verified_models
        items = select_verified_models(caps_need=("text",), min_pass=0.30, only_sota=True, limit=limit, refresh=refresh)
        return [it for it in items if _is_supported_model(it.get("model"))]
    except Exception:
        # degrade gracefully
        return [{"model": m, "pass_rate": None, "hint": None} for m in _static_candidates()[:limit]]


def _official_candidates(limit: int = 50) -> List[Dict[str, Any]]:
    """Return a best-effort list of 'official' models.

    Priority:
    1) Local file data/llm/official/models.txt (lines: provider|model or model)
    2) g4f library introspection (heuristic)
    """
    out: List[Dict[str, Any]] = []
    # 1) Local file seed
    txt = Path('data/llm/official/models.txt')
    if txt.exists():
        try:
            for line in txt.read_text(encoding='utf-8').splitlines():
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if '|' in s:
                    prov, model = s.split('|', 1)
                    out.append({"model": model.strip(), "hint": prov.strip(), "pass_rate": None})
                else:
                    out.append({"model": s, "hint": None, "pass_rate": None})
        except Exception:
            pass
    # 2) g4f introspection (best-effort)
    if not out:
        try:
            import g4f
            # Heuristic: scan attributes that look like model name lists
            cand = []
            for name in dir(g4f):
                if name.lower() in ("models", "model"):  # common pattern
                    try:
                        val = getattr(g4f, name)
                        if isinstance(val, (list, tuple)):
                            cand.extend(str(x) for x in val if isinstance(x, (str,)))
                        elif isinstance(val, dict):
                            cand.extend(str(k) for k in val.keys())
                    except Exception:
                        continue
            cand = [c for c in cand if c and isinstance(c, str)]
            # unique preserve
            seen = set(); ordered = []
            for c in cand:
                if c not in seen:
                    seen.add(c); ordered.append(c)
            for m in ordered:
                out.append({"model": m, "hint": None, "pass_rate": None})
        except Exception:
            pass
    # clip
    uniq = []
    seen = set()
    for it in out:
        m = it.get('model')
        if m and m not in seen:
            seen.add(m); uniq.append(it)
    filtered = [it for it in uniq if _is_supported_model(it.get("model"))]
    return filtered[:limit]


def _probe_model(model_name: str, system: Optional[str] = None, prompt: Optional[str] = None,
                 providers_per_model: int = 4, tries_per_model: int = 2, timeout: int = 60,
                 provider_id: Optional[str] = None) -> ModelProbe:
    system = system or "Tu es un analyste macro‑financier factuel et concis."
    prompt = prompt or "Donne 3 risques macro majeurs à surveiller cette semaine (puces courtes)."
    provider_hint = None
    try:
        from runners.sanity_runner_ia_chat import ask_with_specific_model
        kwargs = dict(prompt=prompt, system=system,
                      providers_per_model=providers_per_model,
                      tries_per_model=tries_per_model,
                      timeout=timeout)
        if provider_id:
            kwargs["provider"] = provider_id
        # ensure openrouter key is visible to downstream client if present
        if OPENROUTER_API_KEY and "OPENROUTER_API_KEY" not in os.environ:
            os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
        res = ask_with_specific_model(model_name, **kwargs)
        provider_hint = res.get("provider")
        return ModelProbe(model=model_name, ok=bool(res.get("ok")), provider=provider_hint, latency_s=res.get("latency_s"))
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        return ModelProbe(model=model_name, ok=False, provider=provider_hint, latency_s=None, error=err, endpoint=provider_id)


# Async probing (for parallel testing)
import asyncio  # kept local to avoid breaking sync usage


async def _probe_model_async(model_name: str, system: Optional[str] = None, prompt: Optional[str] = None,
                             providers_per_model: int = 4, tries_per_model: int = 2, timeout: int = 60,
                             provider_id: Optional[str] = None) -> ModelProbe:
    return await asyncio.to_thread(
        _probe_model,
        model_name,
        system,
        prompt,
        providers_per_model,
        tries_per_model,
        timeout,
        provider_id,
    )


def refresh(limit: int = 8, refresh_verified: bool = True) -> Path:
    import os
    source = os.getenv('G4F_SOURCE', 'both').lower().strip()
    cand: List[Dict[str, Any]] = []
    if source in ('verified', 'both'):
        for it in _verified_candidates(limit=limit, refresh=refresh_verified):
            it = dict(it); it['__source'] = 'verified'; cand.append(it)
    if source in ('official', 'both'):
        for it in _official_candidates(limit=limit):
            it = dict(it); it['__source'] = 'official'; cand.append(it)
    # Deduplicate by model preserving order
    seen = set(); merged: List[Dict[str, Any]] = []
    for it in cand:
        m = it.get('model')
        if m and m not in seen:
            seen.add(m); merged.append(it)
    if not merged:
        merged = [{"model": m, "pass_rate": None, "hint": None, "__source": None} for m in _static_candidates()[:limit]]
    out: List[ModelProbe] = []
    for c in merged:
        m = c.get("model") if isinstance(c, dict) else str(c)
        if not _is_supported_model(m):
            continue
        pr = ModelProbe(model=m, ok=False, provider=None, latency_s=None, pass_rate=c.get("pass_rate") if isinstance(c, dict) else None)
        try:
            probe = _probe_model(m, timeout=60)
            probe.source = c.get('__source')
            probe.pass_rate = pr.pass_rate
            out.append(probe)
        except Exception:
            pr.source = c.get('__source')
            out.append(pr)
        # small pacing to avoid hammering providers
        time.sleep(0.5)
    return _save_working(out)


def load_working_models(max_age_hours: int = 24) -> List[str]:
    obj = _load_working()
    try:
        asof = obj.get("asof")
        if asof:
            dt = datetime.fromisoformat(asof.replace("Z","+00:00"))
            age_h = (datetime.now(timezone.utc) - dt).total_seconds()/3600.0
            if age_h > max_age_hours:
                return []
    except Exception:
        pass
    rows = obj.get("models") or []
    rows = [r for r in rows if _is_supported_model(r.get("model"))]
    # Sort by ok desc, pass_rate desc, latency asc
    rows.sort(key=lambda r: (not bool(r.get("ok")), (r.get("latency_s") or 9999.0), -(r.get("pass_rate") or 0.0), (r.get("model") or "").lower()))
    models = [r.get("model") for r in rows if r.get("ok")]
    return models[:MAX_STORED_MODELS or len(models)]


def merge_from_working_txt(txt_path: Path) -> Path:
    """Merge provider|model|media_type lines into working.json, marking them ok.

    Lines format: provider|model|media_type
    Unknown latency/pass_rate will be left as None.
    """
    if isinstance(txt_path, str):
        txt_path = Path(txt_path)
    models: List[ModelProbe] = []
    try:
        with txt_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '|' not in line:
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    provider, model = parts[0].strip(), parts[1].strip()
                    if not _is_supported_model(model):
                        continue
                    models.append(ModelProbe(model=model, ok=True, provider=provider, latency_s=None, pass_rate=None))
    except Exception:
        pass
    if not models:
        return WORKING_PATH
    # Load existing and union by model name (prefer existing with latency)
    current = _load_working()
    cur_map: Dict[str, Dict[str, Any]] = {m.get('model'): m for m in (current.get('models') or [])}
    for pr in models:
        if pr.model not in cur_map:
            cur_map[pr.model] = asdict(pr)
        else:
            # ensure ok stays True
            cur_map[pr.model]['ok'] = True
            if not cur_map[pr.model].get('provider'):
                cur_map[pr.model]['provider'] = pr.provider
    merged = [ModelProbe(**{**x, 'tested_at': x.get('tested_at') or _now_iso()}) for x in cur_map.values()]
    # Keep deterministic order: ok first, then name
    merged.sort(key=lambda r: (not r.ok, (r.model or '').lower()))
    return _save_working(merged)


def merge_from_remote(url: Optional[str] = None) -> Path:
    """Fetch a remote working list (provider|model|media_type per line) and merge into working.json.
    Defaults to DEFAULT_REMOTE_URL. Marks entries ok=True with provider set; latency/pass_rate remain None.
    """
    import urllib.request
    url = url or DEFAULT_REMOTE_URL
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        # No change if fetch fails
        return WORKING_PATH

    lines = [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.startswith("#")]
    # Build probes from lines
    new_models: List[ModelProbe] = []
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 2:
            provider, model = parts[0].strip(), parts[1].strip()
            if model and _is_supported_model(model):
                new_models.append(ModelProbe(model=model, ok=True, provider=provider, latency_s=None, pass_rate=None))
    if not new_models:
        return WORKING_PATH

    current = _load_working()
    cur_map: Dict[str, Dict[str, Any]] = {m.get('model'): m for m in (current.get('models') or [])}
    for pr in new_models:
        if pr.model not in cur_map:
            cur_map[pr.model] = asdict(pr)
        else:
            cur_map[pr.model]['ok'] = True
            if not cur_map[pr.model].get('provider'):
                cur_map[pr.model]['provider'] = pr.provider
    merged = [ModelProbe(**{**x, 'tested_at': x.get('tested_at') or _now_iso()}) for x in cur_map.values()]
    # Keep deterministic order: ok first, then name
    merged.sort(key=lambda r: (not r.ok, (r.model or '').lower()))
    return _save_working(merged)


def merge_from_working_results(url: Optional[str] = None, limit: int = 64) -> Path:
    """
    Fetch working_results.txt (provider|model|media_type per line), keep only premium models
    and providers of interest (OpenRouter/DeepInfra), and merge into working.json.
    Marks ok=True with provider set; latency/pass_rate remain None.
    """
    import urllib.request
    url = url or DEFAULT_WORKING_RESULTS_URL
    premium_providers = {"openrouter", "openrouterai", "deepinfra", "deep-infra"}
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return WORKING_PATH

    lines = [ln.strip() for ln in content.splitlines() if ln.strip() and not ln.startswith("#")]
    new_models: List[ModelProbe] = []
    for line in lines:
        parts = line.split("|")
        if len(parts) >= 2:
            provider, model = parts[0].strip(), parts[1].strip()
            if not provider or not model:
                continue
            if provider.lower() not in premium_providers:
                continue
            if not _is_supported_model(model) or not _is_premium_model(model):
                continue
            new_models.append(ModelProbe(model=model, ok=True, provider=provider, latency_s=None, pass_rate=None, source="working_results"))
            if limit and len(new_models) >= limit:
                break
    if not new_models:
        return WORKING_PATH

    current = _load_working()
    cur_map: Dict[str, Dict[str, Any]] = {m.get('model'): m for m in (current.get('models') or [])}
    for pr in new_models:
        if pr.model not in cur_map:
            cur_map[pr.model] = asdict(pr)
        else:
            cur_map[pr.model]['ok'] = True
            if not cur_map[pr.model].get('provider'):
                cur_map[pr.model]['provider'] = pr.provider
            if not cur_map[pr.model].get('source'):
                cur_map[pr.model]['source'] = pr.source
    merged = [ModelProbe(**{**x, 'tested_at': x.get('tested_at') or _now_iso()}) for x in cur_map.values()]
    merged.sort(key=lambda r: (not r.ok, (r.model or '').lower()))
    return _save_working(merged)


def merge_from_lines(lines: List[str]) -> Path:
    """Merge provider|model|media_type lines into working.json (marks ok=True)."""
    new_models: List[ModelProbe] = []
    for line in lines or []:
        if not line or '|' not in line:
            continue
        parts = line.split('|')
        if len(parts) >= 2:
            provider, model = parts[0].strip(), parts[1].strip()
            if model and _is_supported_model(model):
                new_models.append(ModelProbe(model=model, ok=True, provider=provider, latency_s=None, pass_rate=None))
    if not new_models:
        return WORKING_PATH
    current = _load_working()
    cur_map: Dict[str, Dict[str, Any]] = {m.get('model'): m for m in (current.get('models') or [])}
    for pr in new_models:
        if pr.model not in cur_map:
            cur_map[pr.model] = asdict(pr)
        else:
            cur_map[pr.model]['ok'] = True
            if not cur_map[pr.model].get('provider'):
                cur_map[pr.model]['provider'] = pr.provider
    merged = [ModelProbe(**{**x, 'tested_at': x.get('tested_at') or _now_iso()}) for x in cur_map.values()]
    merged.sort(key=lambda r: (not r.ok, (r.model or '').lower()))
    return _save_working(merged)


def prune_working_models() -> Path:
    """Trim working.json to supported entries only."""
    raw = _load_working()
    rows = raw.get("models") or []
    probes: List[ModelProbe] = []
    for row in rows:
        try:
            probes.append(
                ModelProbe(
                    model=row.get("model"),
                    ok=bool(row.get("ok")),
                    provider=row.get("provider"),
                    latency_s=row.get("latency_s"),
                    pass_rate=row.get("pass_rate"),
                    source=row.get("source"),
                    tested_at=row.get("tested_at") or _now_iso(),
                )
            )
        except Exception:
            continue
    if not probes:
        probes = [ModelProbe(model=m, ok=False, provider=None, latency_s=None) for m in _static_candidates()]
    return _save_working(probes)


def ensure_working_models(limit: int = 8, max_age_hours: int = 6, min_ok: int = 2) -> List[str]:
    """Return a fresh list of supported models, refreshing the watcher if needed."""
    # Always try to merge the latest premium working_results (OpenRouter/DeepInfra) first
    try:
        merge_from_working_results()
    except Exception:
        pass
    models = load_working_models(max_age_hours=max_age_hours)
    if len(models) >= min_ok:
        return models[:limit]
    # attempt prune + refresh
    try:
        prune_working_models()
    except Exception:
        pass
    try:
        refresh(limit=limit, refresh_verified=True)
    except Exception:
        # ignore refresh errors – we'll fall back shortly
        pass
    models = load_working_models(max_age_hours=max_age_hours * 2)
    if models:
        return models[:limit]
    fallback = [m for m in _static_candidates() if _is_supported_model(m)]
    return fallback[:limit] or _static_candidates()[:limit]


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="G4F Model Watcher")
    p.add_argument("--refresh", action="store_true", help="Refresh working models and write JSON")
    p.add_argument("--limit", type=int, default=int(os.getenv("G4F_TEST_LIMIT","8")))
    p.add_argument("--merge-remote", action="store_true", help="Merge remote working list into working.json before probing")
    p.add_argument("--remote-url", type=str, default=DEFAULT_REMOTE_URL)
    p.add_argument("--no-refresh-verified", action="store_true", help="Skip refreshing verified list, use cache")
    p.add_argument("--ensure", action="store_true", help="Ensure working models exist (refresh if stale) and print them")
    p.add_argument("--prune", action="store_true", help="Prune working.json to supported/limited entries only")
    args = p.parse_args(argv)
    if args.prune:
        path = prune_working_models()
        print(json.dumps({"ok": True, "path": str(path)}, ensure_ascii=False))
        return 0
    if args.ensure:
        models = ensure_working_models(limit=args.limit)
        print(json.dumps({"ok": True, "models": models}, ensure_ascii=False))
        return 0
    if args.refresh:
        if args.merge_remote:
            merge_from_remote(args.remote_url)
        path = refresh(limit=args.limit, refresh_verified=(not args.no_refresh_verified))
        print(json.dumps({"ok": True, "path": str(path)}, ensure_ascii=False))
        return 0
    # else show current
    print(json.dumps({"ok": True, "models": load_working_models() }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
