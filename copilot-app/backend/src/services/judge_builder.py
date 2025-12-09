"""
Helper pour construire un JudgeVerdict typé (schemas/judge.py) à partir
du dictionnaire brut produit par la route /api/judge (analysis, phases, etc.).
Cette couche normalise notamment les phase_scores et les probabilités de scénarios.
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


def _parse_iso_datetime(dt: str) -> datetime:
    if not dt:
        return datetime.utcnow()
    if isinstance(dt, datetime):
        return dt
    if isinstance(dt, str) and dt.endswith("Z"):
        dt = dt.replace("Z", "+00:00")
    return datetime.fromisoformat(dt)


def _extract_llm_block(row: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    analysis = row.get("analysis")
    raw_answer = row.get("raw_answer")

    if isinstance(analysis, dict):
        return analysis, raw_answer

    for key in ("raw_answer", "verdict"):
        raw = row.get(key)
        if isinstance(raw, str) and raw.strip():
            try:
                llm_dict = json.loads(raw)
                return llm_dict, raw
            except Exception:
                continue

    return {"error": "no_json"}, raw_answer


def _normalize_phase_scores(
    row_phase_scores: Optional[Dict[str, Any]],
    llm_phase_scores: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
    raw: Dict[str, float] = {}
    norm: Dict[str, float] = {}

    row_phase_scores = row_phase_scores or {}

    for k, v in row_phase_scores.items():
        try:
            x = float(v)
        except Exception:
            continue
        raw[k] = x
        x_norm = x / 100.0 if x > 1.0 else x
        if x_norm < 0.0:
            x_norm = 0.0
        if x_norm > 1.0:
            x_norm = 1.0
        norm[k] = x_norm

    if isinstance(llm_phase_scores, dict):
        for k, v in llm_phase_scores.items():
            if k not in norm:
                try:
                    x = float(v)
                except Exception:
                    continue
                x_norm = x / 100.0 if x > 1.0 else x
                if x_norm < 0.0:
                    x_norm = 0.0
                if x_norm > 1.0:
                    x_norm = 1.0
                norm[k] = x_norm

    return norm, (raw or None)


def _build_phases(row: Dict[str, Any]) -> Optional[Phases]:
    phases_raw = row.get("phases")
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


def _build_attachments(row: Dict[str, Any]) -> List[NewsAttachment]:
    raw_attachments = row.get("attachments") or []
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
    candidate = row.get("ml_prior") or llm_dict.get("ml_prior")
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


def _compute_direction(expected_return: float, eps: float = 1e-6) -> Optional[str]:
    if expected_return > eps:
        return "up"
    if expected_return < -eps:
        return "down"
    return "flat"


def build_judge_verdict(row: Dict[str, Any], profile: Optional[str] = None) -> JudgeVerdict:
    """
    Transforme un row brut (issu du pipeline judge) en JudgeVerdict Pydantic.
    """
    llm_dict, raw_answer = _extract_llm_block(row)

    ticker = row.get("ticker") or row.get("features", {}).get("ticker") or "UNKNOWN"
    expected_return = float(row.get("expected_return", 0.0))
    expected_return_ensemble = row.get("expected_return_ensemble")
    expected_return_raw = row.get("expected_return_raw")
    confidence = float(row.get("confidence", llm_dict.get("confidence", 0.0)))

    risk_level = row.get("risk_level", "medium")
    if risk_level not in ("low", "medium", "high"):
        risk_level = "medium"

    horizon = (
        row.get("horizon")
        or row.get("ml_prior", {}).get("horizon")
        or llm_dict.get("ml_prior", {}).get("horizon")
        or "1w"
    )

    summary = llm_dict.get("summary") or []
    if isinstance(summary, str):
        summary = [summary]

    scenarios: List[Scenario] = []
    scenarios_raw = llm_dict.get("scenarios") or []
    if isinstance(scenarios_raw, list):
        for sc in scenarios_raw:
            if not isinstance(sc, dict):
                continue
            try:
                scenarios.append(
                    Scenario(
                        name=str(sc.get("name", "unknown")),
                        p=sc.get("p", 0.0),
                        description=sc.get("description"),
                    )
                )
            except ValidationError:
                continue

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

    row_phase_scores = row.get("phase_scores_raw") or row.get("phase_scores")
    llm_phase_scores = llm_dict.get("phase_scores")
    phase_scores, phase_scores_raw = _normalize_phase_scores(
        row_phase_scores=row_phase_scores,
        llm_phase_scores=llm_phase_scores,
    )

    phases = _build_phases(row)
    attachments = _build_attachments(row)
    ml_prior = _build_ml_prior(row, llm_dict)

    generated_at_str = row.get("generated_at") or row.get("meta", {}).get("generated_at")
    generated_at = (
        _parse_iso_datetime(generated_at_str)
        if generated_at_str
        else datetime.utcnow()
    )

    model_version = row.get("model_version") or llm_dict.get("model")
    provider = None
    debug_llm_res = row.get("debug_llm_res")
    if isinstance(debug_llm_res, dict):
        provider = debug_llm_res.get("provider") or provider

    source = row.get("source")
    data_ts = None
    try:
        meta_in = row.get("meta") or {}
        if isinstance(meta_in, dict) and meta_in.get("data_timestamps"):
            data_ts = meta_in.get("data_timestamps")
    except Exception:
        data_ts = None

    meta = VerdictMeta(
        generated_at=generated_at,
        model_version=model_version,
        provider=provider,
        profile=profile,
        source=source if isinstance(source, list) else None,
        data_timestamps=data_ts,
    )

    quant_confidence: Optional[float] = None
    if ml_prior is not None:
        quant_confidence = ml_prior.confidence

    verdict = JudgeVerdict(
        ticker=ticker,
        horizon=horizon,
        direction=_compute_direction(expected_return),
        expected_return=expected_return,
        expected_return_ensemble=expected_return_ensemble,
        expected_return_raw=expected_return_raw,
        risk_level=risk_level,
        confidence=confidence,
        quant_confidence=quant_confidence,
        summary=list(summary),
        scenarios=scenarios,
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
        debug_payload=row.get("debug_payload"),
        debug_llm_res=debug_llm_res,
    )

    return verdict
