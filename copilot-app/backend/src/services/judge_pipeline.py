"""
Judge pipeline (monolith structuré, pas de micro-fichiers).
But: scorer news, assembler le payload, valider, parser la réponse LLM, et tracer les métriques.

Contraintes:
- Pas de cache silencieux, pas de fallback: si une donnée manque, on remonte l'erreur explicitement.
- Live-only pour ML prior (yfinance), news top-5, macro avec deltas.
- JSON LLM strict: dernière ligne = JSON obligatoire.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, validator

# ==== Data models (validation stricte) ====

class NewsItem(BaseModel):
    title: str = Field(..., max_length=300)
    sent: Optional[float] = Field(None, ge=-1, le=1)
    ts: Optional[str]
    source: Optional[str]
    summary: Optional[str] = Field(None, max_length=300)
    tickers: List[str] = Field(default_factory=list, max_items=20)
    age_hours: Optional[float] = None

class PhaseScores(BaseModel):
    fundamental: Optional[float] = None
    technical: Optional[float] = None
    macro: Optional[float] = None
    sentiment: Optional[float] = None
    fusion: Optional[float] = None

class MlPrior(BaseModel):
    pred_return: Optional[float] = None
    confidence: Optional[float] = Field(None, ge=0, le=1)
    horizon: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None

class JudgePayload(BaseModel):
    ticker: str = Field(..., regex=r"^[A-Z0-9]{1,8}$")
    features: Dict[str, Any]
    phases: Dict[str, Any]
    news: List[NewsItem] = Field(default_factory=list, max_items=5)
    attachments: Optional[List[Dict[str, Any]]] = None
    locale: str = "fr-FR"
    meta: Dict[str, Any]
    ml_prior: Optional[MlPrior] = None
    phase_scores: Optional[PhaseScores] = None

class LLMResponse(BaseModel):
    summary: List[str]
    scenarios: List[Dict[str, Any]]
    risks: List[str]
    impacts: Dict[str, Any]
    actions: List[str]
    confidence: Optional[float]
    data_needed: Optional[List[str]] = None
    phase_scores: Optional[Dict[str, Any]] = None
    ml_prior: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @validator("phase_scores")
    def _phase_scores_numeric(cls, v):
        if v is None:
            return v
        for _, val in v.items():
            if val is not None and not isinstance(val, (int, float)):
                raise ValueError("phase_scores must be numeric or null")
        return v

    @validator("confidence")
    def _conf_range(cls, v):
        if v is None:
            return v
        if not (0.0 <= float(v) <= 1.0):
            raise ValueError("confidence must be in [0,1]")
        return v

# ==== Helpers ====

def score_news(news_list: List[Dict[str, Any]], cap: int = 5) -> List[Dict[str, Any]]:
    def _parse_ts(ts):
        if not ts:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(ts, fmt)
            except Exception:
                continue
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None

    now = datetime.utcnow()
    scored: List[Tuple[Optional[datetime], float, Dict[str, Any]]] = []
    for n in news_list:
        ts = n.get("timestamp") or n.get("ts") or n.get("published_at") or n.get("date")
        dt = _parse_ts(ts)
        sent_raw = n.get("sentiment_score") or n.get("sent") or n.get("sentiment")
        try:
            sent_abs = abs(float(sent_raw)) if sent_raw is not None else 0.0
        except Exception:
            sent_abs = 0.0
        scored.append((dt, sent_abs, n))
    scored.sort(key=lambda x: ((x[0] or datetime.min), x[1]), reverse=True)
    top = []
    for dt, sent_abs, n in scored[:cap]:
        age_hours = None
        if dt:
            age_hours = max(0.0, (now - dt).total_seconds() / 3600.0)
        top.append(
            {
                "title": n.get("title") or n.get("headline"),
                "sent": n.get("sentiment_score") or n.get("sent") or n.get("sentiment"),
                "ts": n.get("timestamp") or n.get("ts") or n.get("published_at") or n.get("date"),
                "source": n.get("source"),
                "summary": (n.get("summary") or n.get("description") or (n.get("raw_text") or ""))[:100],
                "tickers": n.get("tickers") or n.get("symbols") or [],
                "age_hours": age_hours,
            }
        )
    return top


def compute_fusion_score(phases: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a simple fusion score as mean of available phase scores."""
    if not phases or not isinstance(phases, dict):
        return {}
    scores = []
    for k in ("fundamental", "technical", "macro", "sentiment", "fusion"):
        try:
            v = phases.get(k, {}).get("score") if isinstance(phases.get(k), dict) else None
            if v is not None:
                scores.append(float(v))
        except Exception:
            continue
    if not scores:
        return {}
    fusion_val = sum(scores) / len(scores)
    dominant = max(
        ((k, phases.get(k, {}).get("score")) for k in ("fundamental", "technical", "macro", "sentiment") if isinstance(phases.get(k), dict) and phases.get(k, {}).get("score") is not None),
        key=lambda x: x[1],
        default=(None, None),
    )[0]
    return {
        "score": fusion_val,
        "dominant_phase": dominant,
        "count": len(scores),
    }
def parse_llm_answer(answer: str) -> Dict[str, Any]:
    if not answer:
        return {"error": "empty_answer"}
    tail = answer.strip().splitlines()
    for line in reversed(tail):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict) and {"summary", "scenarios", "risks", "impacts", "actions", "confidence"} <= set(obj.keys()):
                return obj
        except Exception:
            continue
    try:
        start = answer.rfind("{")
        if start != -1:
            snippet = answer[start:]
            obj = json.loads(snippet)
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {
        "error": "json_parse_failed",
        "summary": [answer],
        "scenarios": [],
        "risks": [],
        "impacts": {},
        "actions": [],
        "confidence": None,
    }

# ==== Metrics helper ====

def timed(func):
    """Decorator to measure elapsed ms for a function."""
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        out = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return out, elapsed_ms
    return wrapper

# ==== Logging / Metrics ====
try:
    import structlog
    logger = structlog.get_logger()
except Exception:
    class _FallbackLogger:
        def info(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
    logger = _FallbackLogger()

def log_metrics(event: str, **fields):
    """Structured logging helper (no-op if structlog unavailable)."""
    try:
        logger.info(event, **fields)
    except Exception:
        pass

from dataclasses import dataclass, field, asdict

@dataclass
class JudgeMetrics:
    """
    Metrics tracker for judge pipeline execution.
    
    Tracks:
    - Latencies per step (ms)
    - LLM costs (tokens + USD)
    - Data quality (news count, phases, etc)
    - Errors
    """
    ticker: str
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    # Latencies (milliseconds)
    data_load_ms: float = 0.0
    news_scoring_ms: float = 0.0
    payload_build_ms: float = 0.0
    ml_prior_ms: float = 0.0
    llm_call_ms: float = 0.0
    parse_response_ms: float = 0.0
    total_ms: float = 0.0
    
    # Data quality
    news_raw_count: int = 0
    news_scored_count: int = 0
    phases_computed: int = 0
    
    # LLM tracking
    llm_model: Optional[str] = None
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_cost_usd: float = 0.0
    llm_retries: int = 0
    
    # Results
    confidence_final: float = 0.0
    parse_success: bool = False
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    # Cache (for future use)
    used_cache: bool = False
    
    def calculate_cost(self, cost_per_1m_in: float = 0.15, cost_per_1m_out: float = 0.60):
        """
        Calculate LLM cost from tokens.
        
        Default pricing (approximate for GPT-4 level models):
        - Input: $0.15 per 1M tokens
        - Output: $0.60 per 1M tokens
        """
        cost_in = (self.llm_tokens_in / 1_000_000) * cost_per_1m_in
        cost_out = (self.llm_tokens_out / 1_000_000) * cost_per_1m_out
        self.llm_cost_usd = cost_in + cost_out
        return self.llm_cost_usd
    
    def finalize(self):
        """Calculate total time and cost."""
        self.total_ms = sum([
            self.data_load_ms,
            self.news_scoring_ms,
            self.payload_build_ms,
            self.ml_prior_ms,
            self.llm_call_ms,
            self.parse_response_ms,
        ])
        if self.llm_tokens_in > 0 or self.llm_tokens_out > 0:
            self.calculate_cost()
    
    def to_dict(self):
        """Convert to dict for logging."""
        return asdict(self)
    
    def log_summary(self):
        """Return a human-readable summary string."""
        return (
            f"[{self.ticker}] "
            f"Total: {self.total_ms:.0f}ms, "
            f"LLM: {self.llm_call_ms:.0f}ms ({self.llm_model or 'unknown'}), "
            f"Cost: ${self.llm_cost_usd:.4f}, "
            f"Confidence: {self.confidence_final:.2f}, "
            f"Errors: {len(self.errors)}"
        )


# ==== Pipeline (callable from route) ====

def build_payload(
    ticker: str,
    features: Dict[str, Any],
    macro: Dict[str, Any],
    news: List[Dict[str, Any]],
    attachments: Optional[List[Dict[str, Any]]],
    phases: Dict[str, Any],
    ml_prior: Optional[Dict[str, Any]],
    locale: str = "fr-FR",
) -> JudgePayload:
    # Attach macro, phases, news_count, ml_prior in features/meta for context
    merged_features = {**features}
    merged_features["macro"] = macro
    merged_features["news_count"] = len(news)
    merged_features["phases"] = phases
    merged_features["ml_prior"] = ml_prior

    payload_raw = {
        "ticker": ticker,
        "features": merged_features,
        "phases": phases or {},
        "phase_scores": phases.get("scores") if isinstance(phases, dict) else None,
        "news": news,
        "attachments": attachments,
        "locale": locale,
        "meta": {
            "source": "judge_pipeline",
            "ticker": ticker,
            "ml_prior": ml_prior,
            "data_timestamps": {
                "macro": macro.get("cpi_last_date"),
            },
        },
        "ml_prior": ml_prior,
    }
    return JudgePayload(**payload_raw)


def validate_llm_response(parsed: Dict[str, Any]) -> LLMResponse:
    return LLMResponse(**parsed)


def time_ms() -> float:
    return time.perf_counter() * 1000.0
