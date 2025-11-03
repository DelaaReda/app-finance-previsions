from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Dict

from .runtime import LLMClient
from .schemas import LLMEnsembleSummary
from .toolkit import REGISTRY


PROMPT_SYS = (
    "Tu es un analyste marchés. Tu dois produire un JSON strict conforme au schéma.\n"
    "Règles: 1) Ne mets que du JSON. 2) Si une donnée manque, mets null. 3) 'key_drivers' court et précis."
)

PROMPT_USER = (
    "Constitue un résumé multi-agents à partir de ces inputs (réduits si volumineux):\n"
    "INPUTS_JSON={inputs}\n"
    "SCHEMA_JSON={schema}\n"
)


def _inputs_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for name in ["freshness_status", "load_macro", "load_forecasts"]:
        try:
            if name in REGISTRY:
                snap[name] = REGISTRY[name].call()
        except Exception as e:
            snap[name] = {"ok": False, "error": str(e)}
    return snap


def run_llm_summary(save_base: str = "data/llm_summary") -> LLMEnsembleSummary:
    client = LLMClient(provider="g4f", model=os.getenv("LLM_SUMMARY_MODEL", "deepseek-ai/DeepSeek-R1-0528"))
    inputs = _inputs_snapshot()
    schema = LLMEnsembleSummary.model_json_schema()

    messages = [
        {"role": "system", "content": PROMPT_SYS},
        {"role": "user", "content": PROMPT_USER.format(inputs=json.dumps(inputs)[:15000], schema=json.dumps(schema))},
    ]
    raw = client.generate(messages, json_mode=True, temperature=0.2, max_tokens=1500, retries=2)
    data = json.loads(raw)
    summary = LLMEnsembleSummary.model_validate(data)

    # persist partition (hourly)
    ts = dt.datetime.utcnow().strftime("%Y%m%d%H")
    outdir = Path(save_base) / f"dt={ts}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "summary.json").write_text(json.dumps(summary.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "trace_raw.json").write_text(json.dumps({"messages": messages, "raw": raw}, ensure_ascii=False), encoding="utf-8")
    return summary

