"""
Helper pour construire un JudgeVerdict typé (schemas/judge.py) à partir
du dictionnaire brut produit par la route /api/judge (analysis, phases, etc.).

Cette couche :
  - extrait le bloc LLM (analysis / raw_answer / verdict)
  - normalise les phase_scores (raw + normalisés)
  - normalise les probabilités de scénarios (0–1)
  - reconstruit un JudgeVerdict canonique pour le frontend.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from pydantic import ValidationError
except Exception:
    ValidationError = Exception  # fallback pour éviter crash si pydantic absent

from schemas.judge import (
    JudgeVerdict,
    Scenario,
    Impacts,
    PhaseScore,
    Phases,
    MLPrior,
    VerdictMeta,
    NewsAttachment,
)


# =====================================================================
# Helpers génériques
# =====================================================================

def _parse_iso_datetime(dt: Any) -> datetime:
    """
    Normalise un timestamp en datetime :
      - datetime → renvoyé tel quel
      - str ISO (avec ou sans Z) → parsé
      - None / vide / invalide → datetime.utcnow()
    """
    if not dt:
        return datetime.utcnow()
    if isinstance(dt, datetime):
        return dt
    if isinstance(dt, str):
        s = dt
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.utcnow()
    return datetime.utcnow()


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


# =====================================================================
# Extraction du bloc LLM (analysis / raw_answer / verdict / debug_llm_res)
# =====================================================================

def _extract_llm_block(row: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Renvoie (llm_dict, raw_answer_str) :
      - llm_dict = dict issu de analysis ou JSON de raw_answer/verdict/debug_llm_res.answer
      - raw_answer_str = la string brute si dispo
    """
    analysis = row.get("analysis")
    raw_answer = row.get("raw_answer")

    # Cas idéal : analysis déjà parsé
    if isinstance(analysis, dict):
        return analysis, raw_answer

    # Fallback : essayer raw_answer ou verdict comme JSON
    for key in ("raw_answer", "verdict"):
        raw = row.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                llm_dict = json.loads(raw)
                return llm_dict, raw
            except Exception:
                continue

    # Fallback supplémentaire : debug_llm_res.answer
    debug_llm_res = row.get("debug_llm_res")
    if isinstance(debug_llm_res, dict):
        ans = debug_llm_res.get("answer")
        if isinstance(ans, str) and ans.strip():
            try:
                llm_dict = json.loads(ans)
                # si raw_answer n'était pas défini, on peut utiliser cette string
                raw_answer = raw_answer or ans
                return llm_dict, raw_answer
            except Exception:
                pass

    # Rien de propre trouvable
    return {"error": "no_json"}, raw_answer


# =====================================================================
# Phase scores : raw + normalisés
# =====================================================================

def _normalize_phase_scores(
    row_phase_scores: Optional[Dict[str, Any]],
    llm_phase_scores: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    """
    Retourne (phase_scores_norm, phase_scores_raw).

    Convention :
      - row_phase_scores = valeurs "brutes" issues du pipeline (peuvent contenir sentiment=79.4, etc.)
      - llm_phase_scores = valeurs normalisées proposées par le LLM (0–1 typiquement)

    Stratégie :
      - phase_scores_raw = cast float(row_phase_scores)
      - phase_scores_norm :
          * pour chaque phase de row_phase_scores :
              - si phase == "sentiment" et score > 1.0 → diviser par 100
              - sinon garder tel quel (en clampant 0–1)
          * ensuite on laisse l'LLM écraser / compléter :
              - si llm_phase_scores[phase] existe → considéré déjà normalisé (clamp 0–1)
    """
    raw: Dict[str, float] = {}
    norm: Dict[str, float] = {}

    row_phase_scores = row_phase_scores or {}

    # 1) Raw baseline (pipeline)
    for k, v in row_phase_scores.items():
        val = _safe_float(v)
        if val is None:
            continue
        raw[k] = val

        # Normalisation par défaut à partir du raw
        if k == "sentiment" and val > 1.0:
            x_norm = val / 100.0
        else:
            x_norm = val

        # clamp
        if x_norm < 0.0:
            x_norm = 0.0
        if x_norm > 1.0:
            x_norm = 1.0
        norm[k] = x_norm

    # 2) Overlay LLM (prioritaire pour la vue "canonique")
    if isinstance(llm_phase_scores, dict):
        for k, v in llm_phase_scores.items():
            val = _safe_float(v)
            if val is None:
                continue
            x_norm = val
            if x_norm < 0.0:
                x_norm = 0.0
            if x_norm > 1.0:
                x_norm = 1.0
            norm[k] = x_norm  # l'LLM écrase ou ajoute

    return norm, (raw or None)


def _build_phases(row: Dict[str, Any]) -> Optional[Phases]:
    """
    Construit le bloc Phases (détails par phase) si disponible.
    On prend en priorité row["phases"], sinon debug_payload.features.phases.
    """
    debug_payload = row.get("debug_payload") or {}
    features = debug_payload.get("features") or {}

    phases_raw = row.get("phases") or features.get("phases")
    if not isinstance(phases_raw, dict):
        return None

    def mk_phase(name: str) -> Optional[PhaseScore]:
        p = phases_raw.get(name)
        if not isinstance(p, dict):
            return None
        score = p.get("score")
        summary = p.get("summary") or []
        details = p.get("details") or {}
        try:
            score_f = float(score)
        except Exception:
            return None
        return PhaseScore(score=score_f, summary=list(summary), details=dict(details))

    return Phases(
        fundamental=mk_phase("fundamental"),
        technical=mk_phase("technical"),
        macro=mk_phase("macro"),
        sentiment=mk_phase("sentiment"),
        fusion=mk_phase("fusion"),
    )


# =====================================================================
# Scénarios : normalisation des probabilités
# =====================================================================

def _normalize_probability(p: Any) -> float:
    """
    Normalise une probabilité :
      - si p > 1, on suppose % → /100
      - clamp dans [0, 1]
    """
    val = _safe_float(p)
    if val is None:
        return 0.0
    if val > 1.0:
        val = val / 100.0
    if val < 0.0:
        val = 0.0
    if val > 1.0:
        val = 1.0
    return val


def _build_scenarios(llm_dict: Dict[str, Any]) -> List[Scenario]:
    scenarios: List[Scenario] = []
    scenarios_raw = llm_dict.get("scenarios") or []
    if not isinstance(scenarios_raw, list):
        return scenarios

    for sc in scenarios_raw:
        if not isinstance(sc, dict):
            continue
        try:
            p_norm = _normalize_probability(sc.get("p", 0.0))
            scenarios.append(
                Scenario(
                    name=str(sc.get("name", "unknown")),
                    p=p_norm,
                    description=sc.get("description"),
                )
            )
        except ValidationError:
            continue

    return scenarios


# =====================================================================
# Attachments & ML prior
# =====================================================================

def _build_attachments(row: Dict[str, Any]) -> List[NewsAttachment]:
    raw_attachments = (
        row.get("attachments")
        or (row.get("debug_payload") or {}).get("attachments")
        or []
    )
    attachments: List[NewsAttachment] = []
    for att in raw_attachments:
        if not isinstance(att, dict):
            continue
        try:
            attachments.append(
                NewsAttachment(
                    title=att.get("title", ""),
                    sent=att.get("sent"),
                    ts=att.get("ts"),
                    source=att.get("source"),
                    summary=att.get("summary"),
                    tickers=att.get("tickers"),
                )
            )
        except ValidationError:
            continue
    return attachments


def _build_ml_prior(row: Dict[str, Any], llm_dict: Dict[str, Any]) -> Optional[MLPrior]:
    dp = row.get("debug_payload") or {}
    features = dp.get("features") or {}

    candidate = (
        row.get("ml_prior")
        or llm_dict.get("ml_prior")
        or features.get("ml_prior")
        or dp.get("ml_prior")
    )

    if not isinstance(candidate, dict):
        return None
    try:
        return MLPrior(
            pred_return=float(candidate.get("pred_return")),
            confidence=float(candidate.get("confidence")),
            horizon=str(candidate.get("horizon", "")),
            source=candidate.get("source"),
        )
    except Exception:
        return None


# =====================================================================
# Direction
# =====================================================================

def _compute_direction(
    expected_return: float,
    row: Dict[str, Any],
) -> Optional[str]:
    """
    Détermine la direction :
      1) row["direction"] si présent
      2) debug_payload.features.direction
      3) signe d'expected_return
    """
    direction = row.get("direction")
    if not isinstance(direction, str):
        dp = row.get("debug_payload") or {}
        features = dp.get("features") or {}
        direction = features.get("direction")

    if direction in ("up", "down", "flat"):
        return direction

    eps = 1e-6
    if expected_return > eps:
        return "up"
    if expected_return < -eps:
        return "down"
    return "flat"


# =====================================================================
# Builder principal
# =====================================================================

def build_judge_verdict(row: Dict[str, Any], profile: Optional[str] = None) -> JudgeVerdict:
    """
    Transforme un row brut (issu du pipeline judge) en JudgeVerdict Pydantic.
    Centralise la normalisation pour éviter d'avoir à toucher la route à chaque fois.
    """
    llm_dict, raw_answer = _extract_llm_block(row)

    raw_debug_payload = row.get("debug_payload")
    debug_payload = (
        raw_debug_payload
        if isinstance(raw_debug_payload, dict) and raw_debug_payload
        else None
    )
    raw_debug_llm_res = row.get("debug_llm_res")
    debug_llm_res = (
        raw_debug_llm_res
        if isinstance(raw_debug_llm_res, dict) and raw_debug_llm_res
        else None
    )
    features = (debug_payload or {}).get("features") or {}

    # --- Ticker / horizon ---
    ticker = row.get("ticker") or features.get("ticker") or "UNKNOWN"

    horizon = (
        row.get("horizon")
        or (row.get("ml_prior") or {}).get("horizon")
        or (llm_dict.get("ml_prior") or {}).get("horizon")
        or features.get("horizon")
        or "1w"
    )

    # --- Expected returns ---
    expected_return_raw = row.get("expected_return_raw")
    expected_return_ensemble = row.get("expected_return_ensemble")
    expected_return_value = row.get("expected_return")

    if expected_return_value is None:
        if expected_return_ensemble is not None:
            expected_return_value = expected_return_ensemble
        elif expected_return_raw is not None:
            expected_return_value = expected_return_raw
        else:
            mlp = (
                row.get("ml_prior")
                or llm_dict.get("ml_prior")
                or features.get("ml_prior")
                or {}
            )
            expected_return_value = mlp.get("pred_return", 0.0)

    try:
        expected_return = float(expected_return_value or 0.0)
    except Exception:
        expected_return = 0.0

    # --- Confidence ---
    conf_val = row.get("confidence", llm_dict.get("confidence", 0.0))
    try:
        confidence = float(conf_val)
    except Exception:
        confidence = 0.0

    # --- Risk level ---
    risk_level = str(row.get("risk_level", "medium") or "medium").strip().lower()
    if risk_level not in ("low", "medium", "high", "critical"):
        risk_level = "medium"

    # --- Summary / lists principales ---
    summary = llm_dict.get("summary") or []
    if isinstance(summary, str):
        summary = [summary]

    risks = llm_dict.get("risks") or []
    if isinstance(risks, str):
        risks = [risks]

    actions = llm_dict.get("actions") or []
    if isinstance(actions, str):
        actions = [actions]

    impacts_raw = llm_dict.get("impacts") or {}
    if not isinstance(impacts_raw, dict):
        impacts_raw = {}
    impacts = Impacts(
        FX=impacts_raw.get("FX"),
        rates=impacts_raw.get("rates"),
        commodities=impacts_raw.get("commodities"),
        equity=impacts_raw.get("equity"),
    )

    data_needed = llm_dict.get("data_needed") or []
    if isinstance(data_needed, str):
        data_needed = [data_needed]

    # --- Phase scores (raw + norm) ---
    row_phase_scores = row.get("phase_scores_raw") or row.get("phase_scores")
    llm_phase_scores = llm_dict.get("phase_scores")
    phase_scores, phase_scores_raw = _normalize_phase_scores(
        row_phase_scores=row_phase_scores,
        llm_phase_scores=llm_phase_scores,
    )

    # --- Phases détaillées & autres blocs ---
    phases = _build_phases(row)
    attachments = _build_attachments(row)
    ml_prior = _build_ml_prior(row, llm_dict)

    # --- Meta ---
    # generated_at : row.generated_at > meta.generated_at > debug_payload.meta.generated_at
    generated_at_str = (
        row.get("generated_at")
        or (row.get("meta") or {}).get("generated_at")
        or (debug_payload.get("meta") or {}).get("generated_at")
    )
    generated_at = _parse_iso_datetime(generated_at_str)

    # model_version : row.model_version > meta.model_version > debug_llm_res.model
    model_version = (
        row.get("model_version")
        or (row.get("meta") or {}).get("model_version")
        or (debug_llm_res or {}).get("model")
    )

    provider = None
    row_meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    if isinstance(row.get("provider"), str):
        provider = row.get("provider")
    if not provider and isinstance(row_meta, dict):
        provider = row_meta.get("provider")
    if not provider and isinstance(debug_llm_res, dict):
        provider = debug_llm_res.get("provider")

    source = row.get("source")
    if not isinstance(source, list):
        source = None

    data_ts = None
    data_quality_score = None
    backtest_calibration = None
    try:
        meta_in = row.get("meta") or {}
        if isinstance(meta_in, dict) and meta_in.get("data_timestamps"):
            data_ts = meta_in.get("data_timestamps")
        else:
            dp_meta = (debug_payload or {}).get("meta") or {}
            if isinstance(dp_meta, dict) and dp_meta.get("data_timestamps"):
                data_ts = dp_meta.get("data_timestamps")
        if isinstance(meta_in, dict):
            dqs = meta_in.get("data_quality_score")
            if dqs is not None:
                try:
                    data_quality_score = max(0.0, min(1.0, float(dqs)))
                except Exception:
                    data_quality_score = None
            if isinstance(meta_in.get("backtest_calibration"), dict):
                backtest_calibration = meta_in.get("backtest_calibration")
        if backtest_calibration is None:
            dp_meta = (debug_payload or {}).get("meta") or {}
            if isinstance(dp_meta, dict) and isinstance(dp_meta.get("backtest_calibration"), dict):
                backtest_calibration = dp_meta.get("backtest_calibration")
    except Exception:
        data_ts = None
        data_quality_score = None
        backtest_calibration = None

    meta = VerdictMeta(
        generated_at=generated_at,
        model_version=model_version,
        provider=provider,
        profile=profile,
        source=source,
        data_timestamps=data_ts,
        data_quality_score=data_quality_score,
        backtest_calibration=backtest_calibration,
    )

    # --- Quant confidence ---
    quant_confidence: Optional[float] = None
    if ml_prior is not None:
        quant_confidence = ml_prior.confidence

    # --- Direction ---
    direction = _compute_direction(expected_return, row)

    verdict = JudgeVerdict(
        ticker=ticker,
        horizon=horizon,
        direction=direction,
        expected_return=expected_return,
        expected_return_ensemble=expected_return_ensemble,
        expected_return_raw=expected_return_raw,
        risk_level=risk_level,
        confidence=confidence,
        quant_confidence=quant_confidence,
        summary=list(summary),
        scenarios=_build_scenarios(llm_dict),
        risks=list(risks),
        impacts=impacts,
        actions=list(actions),
        phase_scores=phase_scores,
        phase_scores_raw=phase_scores_raw,
        ml_prior=ml_prior,
        data_needed=list(data_needed),
        phases=phases,
        attachments=attachments,
        analysis=llm_dict if isinstance(llm_dict, dict) else None,
        meta=meta,
        raw_answer=raw_answer,
        debug_payload=debug_payload,
        debug_llm_res=debug_llm_res,
    )

    return verdict
