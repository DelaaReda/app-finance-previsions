#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Turn:
    run_id: str
    turn: int
    round_idx: int
    agent: str
    duration_ms: int
    response_chars: int
    warnings: List[str] = field(default_factory=list)


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            row = json.loads(ln)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _iter_runs(runs_dir: Path, limit: int) -> List[Path]:
    dirs = [p for p in runs_dir.iterdir() if p.is_dir() and p.name[:8].isdigit()]
    dirs.sort(key=lambda p: p.name, reverse=True)
    if limit > 0:
        dirs = dirs[:limit]
    return list(reversed(dirs))


def analyze(runs_dir: Path, limit: int, slow_ms: int, long_chars: int) -> int:
    runs = _iter_runs(runs_dir, limit)
    if not runs:
        print("Aucun run trouvé.")
        return 0

    turns: List[Turn] = []
    total_runs = 0
    total_turns = 0
    warnings_total = 0
    commands_total = 0
    files_total = 0
    rewrites_total = 0

    for run in runs:
        events = _read_jsonl(run / "events.jsonl")
        if not events:
            continue
        total_runs += 1
        for ev in events:
            if ev.get("type") != "turn_response":
                continue
            q = ev.get("quality") or {}
            warnings = list(q.get("warnings") or [])
            turns.append(
                Turn(
                    run_id=run.name,
                    turn=int(ev.get("turn") or 0),
                    round_idx=int(ev.get("round") or 0),
                    agent=str(ev.get("agent") or "?"),
                    duration_ms=int(ev.get("duration_ms") or 0),
                    response_chars=int(ev.get("response_chars") or 0),
                    warnings=warnings,
                )
            )
            total_turns += 1
            warnings_total += len(warnings)
            commands_total += len(ev.get("commands") or [])
            files_total += len(ev.get("files_touched") or [])
            if bool(ev.get("rewritten")):
                rewrites_total += 1

    if total_turns == 0:
        print("Runs trouvés mais aucun turn_response.")
        return 0

    slow = [t for t in turns if t.duration_ms >= slow_ms]
    long_resp = [t for t in turns if t.response_chars >= long_chars]
    with_warn = [t for t in turns if t.warnings]

    print("# Orchestrator Run Analysis")
    print("")
    print(f"- runs analysés: {total_runs}")
    print(f"- turns: {total_turns}")
    print(f"- warnings: {warnings_total}")
    print(f"- commandes détectées: {commands_total}")
    print(f"- fichiers touchés détectés: {files_total}")
    print(f"- réponses réécrites automatiquement: {rewrites_total}")
    print(f"- tours lents (>{slow_ms}ms): {len(slow)}")
    print(f"- réponses longues (>{long_chars} chars): {len(long_resp)}")
    print("")
    print("## Top Slow Turns")
    for t in sorted(slow, key=lambda x: x.duration_ms, reverse=True)[:8]:
        print(
            f"- {t.run_id} turn={t.turn} round={t.round_idx} agent={t.agent} "
            f"duration_ms={t.duration_ms} chars={t.response_chars} warnings={','.join(t.warnings) or '-'}"
        )
    print("")
    print("## Top Long Responses")
    for t in sorted(long_resp, key=lambda x: x.response_chars, reverse=True)[:8]:
        print(
            f"- {t.run_id} turn={t.turn} round={t.round_idx} agent={t.agent} "
            f"chars={t.response_chars} duration_ms={t.duration_ms} warnings={','.join(t.warnings) or '-'}"
        )
    print("")
    print("## Recommendations")
    has_reco = False
    if with_warn and rewrites_total == 0:
        print("- Activer un rewrite automatique quand warnings != 0 (too_long, asks_question, meta_reasoning).")
        has_reco = True
    if rewrites_total > 0:
        print("- Rewrite auto actif: calibrer les triggers pour réduire encore le bruit sans sur-coût.")
        has_reco = True
    if slow:
        print("- Réduire le contexte injecté (memory + team board) et limiter max chars par prompt.")
        has_reco = True
    if long_resp:
        print("- Ajouter une contrainte stricte de longueur par rôle (Tester/Planner) et reformulation auto.")
        has_reco = True
    if commands_total == 0:
        print("- Forcer format 'commandes exécutables' pour Dev/Tester si la tâche le demande.")
        has_reco = True
    if files_total == 0:
        print("- Ajouter une passe Dev opératoire (run shell + patch) au lieu de réponses purement textuelles.")
        has_reco = True
    if not has_reco:
        print("- Les runs sont stables selon les seuils configurés.")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyze qwen_orchestrator run artifacts")
    ap.add_argument("--runs-dir", type=str, default="finance-app/orchestrator-runs")
    ap.add_argument("--limit", type=int, default=8, help="Nombre de runs récents à analyser")
    ap.add_argument("--slow-ms", type=int, default=45000)
    ap.add_argument("--long-chars", type=int, default=3000)
    args = ap.parse_args()

    runs_dir = Path(args.runs_dir).expanduser().resolve()
    if not runs_dir.exists():
        print(f"Runs dir introuvable: {runs_dir}")
        return 1
    return analyze(runs_dir=runs_dir, limit=args.limit, slow_ms=args.slow_ms, long_chars=args.long_chars)


if __name__ == "__main__":
    raise SystemExit(main())
