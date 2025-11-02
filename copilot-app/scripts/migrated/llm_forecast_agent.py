#!/usr/bin/env python3
from __future__ import annotations
"""
LLM Forecast Agent (stub/fallback):
- Reads contexts from data/llm/context/dt=YYYYMMDD/*.json
- Produces data/forecast/dt=YYYYMMDD/llm_agents.json with a simple heuristic verdict

If you have a local g4f proxy and want real calls, replace the heuristic block
with an API call and keep the same output schema.
"""

import json
import os
from typing import Dict
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List

DT_FMT = "%Y%m%d"


def today_dt() -> str:
    # Use timezone-aware UTC to avoid deprecation warnings and ambiguity
    return datetime.now(timezone.utc).strftime(DT_FMT)


def latest_ctx_dir() -> Path | None:
    parts = sorted(Path('data/llm/context').glob('dt=*'))
    return parts[-1] if parts else None


def heuristic_verdict(ctx: Dict) -> Dict:
    # Simple direction based on 1m momentum; confidence scaled by vol/drawdown
    p = ctx.get('prices') or {}
    r1m = p.get('ret_1m') or 0.0
    dd = p.get('max_drawdown') or 0.0
    vol = p.get('vol_1m') or 0.0
    direction = 'up' if r1m > 0.0 else ('down' if r1m < 0.0 else 'flat')
    exp_ret = float(max(-0.05, min(0.05, r1m)))
    base_conf = 0.6 + 0.2 * (1.0 if r1m > 0 else -1.0) * min(abs(r1m)/0.1, 1.0)
    penalty = 0.1 * min(dd, 0.9) + 0.1 * min(vol or 0.0, 0.2)
    conf = float(max(0.1, min(0.95, base_conf - penalty)))
    return {
        "name": "heuristic-judge",
        "direction": direction,
        "expected_return": round(exp_ret, 4),
        "confidence": round(conf, 3),
        "latency_ms": 0,
        "source": "local-heuristic"
    }


def _llm_available() -> bool:
    try:
        from g4f.client import Client as _C  # type: ignore
        return True
    except Exception:
        return False


def _llm_verdict(ctx: Dict) -> Dict:
    """Call g4f client with a strict JSON instruction. Fallback to heuristic on any error."""
    if not _llm_available():
        return heuristic_verdict(ctx)
    try:
        from g4f.client import Client as G4FClient  # type: ignore
        client = G4FClient()
        # Model selection: env LLM_MODEL or a robust default
        model = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3-0324-Turbo")
        sys_prompt = (
            "You are an equity forecasting judge. Output ONLY one valid JSON line. "
            "Keys: direction in ['up','down','flat'], expected_return float in [-0.15,0.15], confidence in [0,1], rationale short."
        )
        # Build compact user content from ctx
        p = ctx.get('prices') or {}
        m = ctx.get('macro') or {}
        news = ctx.get('news') or []
        peers = ctx.get('peers') or []
        summary = {
            "ticker": ctx.get('ticker'),
            "prices": {k: p.get(k) for k in ["last","ret_1m","ret_3m","ret_1y","vol_1m","max_drawdown"]},
            "macro": {k: m.get(k) for k in ["cpi_yoy","yield_curve_slope","recession_prob"]},
            "news_titles": [ (n.get('title') or '')[:120] for n in news[:15] ],
            "peers": peers[:10],
        }
        user = (
            "Context (JSON):\n" + json.dumps(summary, ensure_ascii=False) + "\n\n"
            + "Task: Decide direction for the next 1 month. Conservatively cap absolute expected_return to 0.08."
            + "Return a single JSON line: {\"direction\":\"up|down|flat\",\"expected_return\":0.012,\"confidence\":0.73,\"rationale\":\"...\"}"
        )
        import time
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role":"system","content": sys_prompt},
                {"role":"user","content": user},
            ],
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "256")),
            timeout=int(os.getenv("LLM_TIMEOUT", "45")),
        )
        latency_ms = int((time.perf_counter()-t0)*1000)
        text = (resp.choices[0].message.content if hasattr(resp, "choices") else str(resp)).strip()
        # Extract last JSON line
        parsed: Dict[str, object] | None = None
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    parsed = json.loads(line)
                    break
                except Exception:
                    continue
        if not isinstance(parsed, dict):
            return heuristic_verdict(ctx)
        direction = str(parsed.get('direction','flat')).lower()
        if direction not in ('up','down','flat'):
            direction = 'flat'
        try:
            er = float(parsed.get('expected_return', 0.0))
        except Exception:
            er = 0.0
        try:
            conf = float(parsed.get('confidence', 0.6))
        except Exception:
            conf = 0.6
        # Clamp with env override for absolute cap (default 0.08 display-friendly)
        try:
            cap = float(os.getenv('LLM_MAX_ER', '0.08'))
            cap = max(0.01, min(0.15, cap))
        except Exception:
            cap = 0.08
        er = max(-cap, min(cap, er))
        conf = max(0.0, min(1.0, conf))
        return {
            "name": model,
            "direction": direction,
            "expected_return": round(er, 4),
            "confidence": round(conf, 3),
            "rationale": parsed.get('rationale'),
            "latency_ms": latency_ms,
            "source": "g4f"
        }
    except Exception:
        return heuristic_verdict(ctx)


def main() -> int:
    d = latest_ctx_dir()
    if not d:
        print(json.dumps({"ok": False, "error": "no context directory"}))
        return 1
    tickers: List[Dict] = []
    for fp in sorted(d.glob('*.json')):
        try:
            ctx = json.loads(fp.read_text(encoding='utf-8'))
        except Exception:
            continue
        # Prefer LLM; fallback to heuristic
        use_llm = os.getenv("LLM_USE_G4F", "1") == "1"
        model_out = _llm_verdict(ctx) if use_llm else heuristic_verdict(ctx)
        avg_agreement = float(max(0.0, min(1.0, model_out['confidence'])))
        tickers.append({
            "ticker": ctx.get('ticker'),
            "ensemble": {"avg_agreement": avg_agreement},
            "models": [model_out]
        })
    out = {
        "dt": today_dt(),
        "providers": ["heuristic-judge"],
        "tickers": tickers
    }
    ddir = Path('data/forecast')/f"dt={today_dt()}"
    ddir.mkdir(parents=True, exist_ok=True)
    (ddir/'llm_agents.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({"ok": True, "path": str(ddir/'llm_agents.json'), "tickers": len(tickers)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
