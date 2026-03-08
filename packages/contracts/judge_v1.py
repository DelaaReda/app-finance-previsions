"""
Typed schemas for judge verdicts (Pydantic v1/v2 compatible).

These models define the canonical contract between:
- the judge pipeline (raw dict rows),
- the typed builder (services/judge_builder.py),
- and the frontend.

They are NOT yet wired as FastAPI response_model, but they are
used for validation / normalization and as a reference for the API shape.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

try:
    from pydantic import BaseModel, Field, validator
except ImportError:
    # Minimal shim to avoid hard failure if pydantic absent in runtime env
    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self):
            return self.__dict__

        # pydantic v1 alias
        def dict(self):
            return self.__dict__

        def __repr__(self) -> str:
            fields = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
            return f"{self.__class__.__name__}({fields})"

    def Field(default=None, **kwargs):  # type: ignore
        return default

    def validator(*args, **kwargs):  # type: ignore
        def deco(func):
            return func

        return deco


__all__ = [
    "Scenario",
    "Impacts",
    "PhaseScore",
    "Phases",
    "NewsAttachment",
    "MLPrior",
    "VerdictMeta",
    "JudgeVerdict",
    "JudgeStats",
    "JudgeFiltersApplied",
    "JudgeData",
    "JudgeResponse",
]


# ---------- Basic building blocks ----------


class Scenario(BaseModel):
    """
    Scénario (base / bullish / bearish) avec probabilité normalisée.

    - p est ramené à 0–1 :
      * si le LLM renvoie 60, on le /100
      * si la somme des scénarios != 1, on renormalise au niveau JudgeVerdict.
    """

    name: str = Field(..., description="Nom du scénario, ex: base / bullish / bearish")
    p: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Probabilité (0–1). Si >1 dans le raw, on divisera par 100.",
    )
    description: Optional[str] = None

    @validator("p", pre=True)
    def normalize_probability(cls, v: Any) -> float:
        """Accepte 0–1, 0–100, ou valeurs un peu moches venant du LLM."""
        try:
            x = float(v)
        except Exception:
            raise ValueError(f"Invalid probability value: {v!r}")

        # Cas '60' => 0.60
        if x > 1.0:
            x = x / 100.0

        # Clamp de sécurité
        if x < 0.0:
            x = 0.0
        if x > 1.0:
            x = 1.0

        return x


class Impacts(BaseModel):
    """Impacts par dimension macro / marché. Tous optionnels."""

    FX: Optional[List[str]] = None
    rates: Optional[List[str]] = None
    commodities: Optional[List[str]] = None
    equity: Optional[List[str]] = None


class PhaseScore(BaseModel):
    """
    Détail d'une phase (fundamental / technical / macro / sentiment / fusion).

    - score : idéalement 0–1 normalisé côté pipeline ou builder.
    - summary : quelques bullet points lisibles.
    - details : structure libre pour le frontend (peut être typée plus tard).
    """

    score: float = Field(..., description="Score de phase, idéalement normalisé 0–1")
    summary: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class Phases(BaseModel):
    """Ensemble des phases avec leur score et détails."""

    fundamental: Optional[PhaseScore] = None
    technical: Optional[PhaseScore] = None
    macro: Optional[PhaseScore] = None
    sentiment: Optional[PhaseScore] = None
    fusion: Optional[PhaseScore] = None


class NewsAttachment(BaseModel):
    """Version simplifiée d’un item de news utilisé dans le verdict."""

    title: str
    sent: Optional[str] = Field(
        default=None, description="Sentiment catégoriel, ex: positive / negative / neutral"
    )
    ts: Optional[str] = None
    source: Optional[str] = None
    summary: Optional[str] = None
    tickers: Optional[List[str]] = None


class MLPrior(BaseModel):
    """Résumé du modèle quantitatif (non-LLM)."""

    pred_return: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    horizon: str
    source: Optional[str] = None


class VerdictMeta(BaseModel):
    """Métadonnées sur la génération du verdict."""

    generated_at: datetime
    model_version: Optional[str] = None
    provider: Optional[str] = None
    profile: Optional[str] = None
    source: Optional[List[str]] = None  # ex: ["judge_route", "forecasts_llm"]
    data_timestamps: Optional[Dict[str, Any]] = None
    data_quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    backtest_calibration: Optional[Dict[str, Any]] = None


# ---------- Verdict principal ----------


class JudgeVerdict(BaseModel):
    """
    Verdict canonique retourné par /api/judge (data.verdicts[]).

    Le debug complet reste dans debug_payload / debug_llm_res.
    """

    # Contexte général
    ticker: str
    horizon: str = Field(..., description="Ex: '1w', '1m', '3m'")
    direction: Optional[Literal["up", "down", "flat"]] = Field(
        default=None, description="Direction implicite du move, si calculée"
    )

    # Rendements & risques
    expected_return: float = Field(
        ..., description="Expected return final (post-ensemble), fraction (0.01 = 1%)"
    )
    expected_return_ensemble: Optional[float] = Field(
        default=None, description="Expected return version ensemble"
    )
    expected_return_raw: Optional[float] = Field(
        default=None, description="Expected return brut avant mélange ml_prior"
    )

    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Niveau de risque agrégé (low/medium/high/critical)"
    )

    # Confiance
    confidence: float = Field(..., ge=0.0, le=1.0)
    quant_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confiance purement quantitative (optionnelle)",
    )

    # Explication humaine
    summary: List[str] = Field(default_factory=list)
    scenarios: List[Scenario] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    impacts: Impacts = Field(default_factory=Impacts)
    actions: List[str] = Field(default_factory=list)

    # Scores de phase
    phase_scores: Dict[str, float] = Field(
        default_factory=dict, description="Scores normalisés par phase (0–1)"
    )
    phase_scores_raw: Optional[Dict[str, float]] = Field(
        default=None, description="Version brute (ex: sentiment=76.2) si utile"
    )

    # Quant / LLM
    ml_prior: Optional[MLPrior] = None
    data_needed: List[str] = Field(default_factory=list)

    # Détail par phase + news attachées
    phases: Optional[Phases] = None
    attachments: List[NewsAttachment] = Field(default_factory=list)

    # Analyse brute LLM structurée
    analysis: Optional[Dict[str, Any]] = None

    # Métadonnées et debug
    meta: VerdictMeta

    # Raw + debug complet
    raw_answer: Optional[str] = Field(
        default=None, description="Réponse brute JSON du LLM (string) avant parsing"
    )
    debug_payload: Optional[Dict[str, Any]] = None
    debug_llm_res: Optional[Dict[str, Any]] = None

    # ---------- Validators / helpers ----------

    @validator("phase_scores", pre=True, always=True)
    def ensure_phase_scores_dict(cls, v: Any) -> Dict[str, float]:
        """
        Force un dict str->float.

        Le builder normalise déjà, mais on garde une seconde ligne de défense
        pour éviter des objets bizarres venant d'autres callers éventuels.
        """
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("phase_scores must be a dict")
        return {str(k): float(vv) for k, vv in v.items()}

    @validator("phase_scores_raw", pre=True, always=True)
    def normalize_phase_scores_raw(cls, v: Any) -> Optional[Dict[str, float]]:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("phase_scores_raw must be a dict if provided")
        return {str(k): float(vv) for k, vv in v.items()}

    @validator("scenarios")
    def normalize_scenarios_sum(cls, v: List[Scenario]) -> List[Scenario]:
        """
        Renormalise les probabilités pour que la somme soit 1
        (dans la limite d'une petite tolérance numérique).
        """
        if not v:
            return v
        total = sum(s.p for s in v)
        if total > 0 and abs(total - 1.0) > 1e-6:
            v = [
                Scenario(name=s.name, p=s.p / total, description=s.description)
                for s in v
            ]
        return v


# ---------- Optionnel: types d'enveloppe / réponse ----------


class JudgeStats(BaseModel):
    total_verdicts: int
    high_confidence_count: int
    avg_confidence: float
    generated_at: datetime


class JudgeFiltersApplied(BaseModel):
    min_confidence: float
    tickers: Optional[List[str]] = None
    sort_by: Optional[
        Literal["confidence", "expected_return", "score", "risk_level", "timestamp"]
    ] = "confidence"
    sort_order: Optional[Literal["asc", "desc"]] = "desc"
    limit: int


class JudgeData(BaseModel):
    verdicts: List[JudgeVerdict]
    count: int
    stats: JudgeStats
    filters_applied: JudgeFiltersApplied
    generated_at: datetime
    source: Optional[List[str]] = None
    freshness: Optional[str] = None
    status: Optional[Literal["ok", "degraded", "error"]] = None
    warnings: Optional[List[str]] = None
    runtime: Optional[Dict[str, Any]] = None
    cache: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None
    debug_pipeline: Optional[List[Dict[str, Any]]] = None
    verdicts_raw: Optional[List[Dict[str, Any]]] = None


class JudgeResponse(BaseModel):
    ok: bool
    data: JudgeData
    freshness: str
    status: Optional[Literal["ok", "degraded", "error"]] = None
    error: Optional[str] = None
