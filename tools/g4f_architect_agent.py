"""
G4F Architect Agent — documents the repo architecture and suggests smart wiring

Goal
- Act as a senior software/data/ML systems analyst.
- Read key files in this repo (vision, data flow, Makefile, Dash app/pages, agents, analytics, core).
- Produce a single Markdown report describing:
  1) Current architecture (layers, data flow, partitions, UI)
  2) How to connect modules intelligently for forecasting (agents → partitions → aggregation → evaluation → UI)
  3) Intelligent features roadmap (ensembles, regimes, quality, LLM judge) referencing existing modules
  4) Concrete wiring tasks & milestones (Makefile targets, partition contracts, UI selectors)
  5) Risks, test strategy (unit/e2e), observability plan
- Save to docs/architecture/ARCHITECT_REPORT_YYYYMMDD_HHMM.md

Usage
  PYTHONPATH=src python tools/g4f_architect_agent.py --limit-bytes 120000

Env
  G4F_ARCH_MODEL (default: deepseek-ai/DeepSeek-R1-0528)
  G4F_ARCH_TEMPERATURE (default: 0.2)
  G4F_ARCH_MAX_TOKENS (default: 2200)
"""
from __future__ import annotations

import argparse
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

try:
    from g4f.client import Client as G4FClient
except Exception as e:
    raise RuntimeError("g4f non installé. Fais `pip install -U g4f` dans ton venv.") from e


DEFAULT_MODEL = os.getenv("G4F_ARCH_MODEL", "deepseek-ai/DeepSeek-R1-0528")


def _read_text(p: Path, limit: int) -> str:
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        return txt[:limit]
    except Exception as e:
        return f"(erreur lecture {p}: {e})"


def _tree_snapshot(root: Path, file_limit: int = 350) -> str:
    ignore_dirs = {".git", "node_modules", "logs", "__pycache__", ".venv", "artifacts"}
    files: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        # prune
        dirnames[:] = [d for d in dirnames if d not in ignore_dirs]
        for fn in filenames:
            rp = str((dp / fn).as_posix())
            if any(part in rp for part in ["/.git/", "/node_modules/", "/__pycache__/", "/logs/"]):
                continue
            files.append(rp)
            if len(files) >= file_limit:
                break
        if len(files) >= file_limit:
            break
    return "\n".join(files)


def _collect_context(limit_bytes: int) -> Dict:
    ctx: Dict[str, str] = {}
    # Key docs
    for rel in [
        "docs/architecture/vision.md",
        "docs/architecture/data_flow.md",
        "docs/README.md",
        "AGENTS.md",
        "docs/PROGRESS.md",
        "Makefile",
    ]:
        p = Path(rel)
        if p.exists():
            ctx[rel] = _read_text(p, limit_bytes // 10)
    # Dash app & pages
    for rel in [
        "src/dash_app/app.py",
        "src/dash_app/pages/forecasts.py",
        "src/dash_app/pages/deep_dive.py",
        "src/dash_app/pages/quality.py",
        "src/dash_app/pages/backtests.py",
        "src/dash_app/pages/evaluation.py",
        "src/dash_app/pages/regimes.py",
        "src/dash_app/pages/risk.py",
        "src/dash_app/pages/observability.py",
        "src/dash_app/pages/agents_status.py",
    ]:
        p = Path(rel)
        if p.exists():
            ctx[rel] = _read_text(p, limit_bytes // 12)
    # Agents & analytics
    for rel in [
        "src/agents/equity_forecast_agent.py",
        "src/agents/commodity_forecast_agent.py",
        "src/agents/macro_forecast_agent.py",
        "src/agents/update_monitor_agent.py",
        "src/analytics/phase2_technical.py",
        "src/analytics/phase3_macro.py",
        "src/analytics/econ_llm_agent.py",
    ]:
        p = Path(rel)
        if p.exists():
            ctx[rel] = _read_text(p, limit_bytes // 12)
    # Core
    for rel in [
        "src/core/models.py",
        "src/core/io_utils.py",
        "src/core/market_data.py",
        "src/core/config.py",
    ]:
        p = Path(rel)
        if p.exists():
            ctx[rel] = _read_text(p, limit_bytes // 12)
    # Tree snapshot
    ctx["TREE_SNAPSHOT"] = _tree_snapshot(Path("."))
    return ctx


def _build_prompt(ctx: Dict[str, str]) -> str:
    sections = []
    for k, v in ctx.items():
        sections.append(f"### {k}\n\n{v}\n")
    joined = "\n".join(sections)[:200000]
    return (
        "You are a senior software/data/ML systems analyst.\n"
        "Analyze the following repository context and produce a single comprehensive Markdown report.\n"
        "The report MUST include these sections (use French):\n"
        "1) Architecture actuelle (couches, data flow, contrats de partitions)\n"
        "2) Câblage intelligent des modules de prévision (agents → data/dt=YYYYMMDD → aggregation → evaluation/backtests → UI Dash)\n"
        "3) Fonctionnalités ‘prédiction intelligente’ (ensembles LLM/ML, régimes macro, qualité, juge LLM) avec mapping aux modules existants\n"
        "4) Plan d’implémentation : tâches concrètes + Makefile + schéma de données (parquet/json) + selectors UI\n"
        "5) Stratégie de tests (unit/e2e), observabilité, risques et mitigations\n"
        "6) Annexes : arborescence et fichiers clés\n"
        "Important: sois précis, cite les chemins de fichiers existants, ne propose pas d’appels réseau depuis la UI.\n"
        f"\n===== CONTEXTE REPO =====\n{joined}\n"
    )


def _call_g4f(model: str, prompt: str) -> str:
    client = G4FClient()
    msgs = [
        {"role": "system", "content": "You are a helpful analyst. Do not reveal hidden reasoning."},
        {"role": "user", "content": prompt},
    ]
    res = client.chat.completions.create(
        model=model,
        messages=msgs,
        temperature=float(os.getenv("G4F_ARCH_TEMPERATURE", "0.2")),
        max_tokens=int(os.getenv("G4F_ARCH_MAX_TOKENS", "2200")),
    )
    try:
        return (res.choices[0].message.content or "").strip()
    except Exception:
        return str(res)


def main():
    ap = argparse.ArgumentParser(description="G4F Architect Agent")
    ap.add_argument("--limit-bytes", type=int, default=120000, help="limit bytes per large file")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    ctx = _collect_context(limit_bytes=args.limit_bytes)
    prompt = _build_prompt(ctx)
    out = _call_g4f(args.model, prompt)

    outdir = Path("docs/architecture")
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fp = outdir / f"ARCHITECT_REPORT_{ts}.md"
    fp.write_text(out or "(vide)", encoding="utf-8")
    print(f"Report saved: {fp}")


if __name__ == "__main__":
    main()

