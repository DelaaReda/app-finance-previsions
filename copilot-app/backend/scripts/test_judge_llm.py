"""
Test rapide LLM Judge (standalone, sans API).

Usage :
  cd copilot-app/backend
  PYTHONPATH=src .venv/bin/python scripts/test_judge_llm.py

Ce script :
- charge le 1er ticker de data/forecasts.json
- charge news_feed.json pour fournir des articles complets (pas de réduction)
- appelle EconomicAnalyst.analyze (un seul modèle) avec timeout=120s
- affiche le modèle/provider utilisé et l’erreur éventuelle
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime


def main() -> int:
    try:
        from analytics.econ_llm_agent import EconomicAnalyst, EconomicInput
        from storage.io import load_json
    except Exception as e:
        print(f"[ERR] Imports manquants : {e}")
        return 1

    forecasts = load_json("forecasts") or {}
    rows = forecasts.get("rows") or forecasts.get("data", {}).get("rows", []) or []
    if not rows:
        print("[ERR] Aucun forecast trouvé dans data/forecasts.json")
        return 1

    news_feed = load_json("news_feed") or {}
    articles = news_feed.get("articles") or news_feed.get("data", {}).get("articles", []) or []

    row = rows[0]
    sym = row.get("ticker") or row.get("symbol") or "UNKNOWN"
    print(f"[INFO] Ticker testé: {sym}")

    payload = EconomicInput(
        question=f"Verdict pour {sym} (horizon {row.get('horizon','1w')})",
        features=row,
        news=articles,
        attachments=None,
        locale="fr-FR",
        meta={"source": "scripts/test_judge_llm.py", "generated_at": datetime.utcnow().isoformat() + "Z"},
    )

    agent = EconomicAnalyst(timeout=120, retries_per_model=1)
    print("[INFO] Models candidats (top 5):", agent.model_candidates[:5])

    try:
        res = agent.analyze(payload)
    except Exception as e:
        print(f"[ERR] Exception durant analyze(): {type(e).__name__}: {e}")
        return 1

    ok = res.get("ok")
    print("[INFO] Résultat ok?:", ok)
    print("[INFO] Modèle:", res.get("model"))
    print("[INFO] Provider:", res.get("provider"))
    print("[INFO] Erreur:", res.get("error"))
    answer = res.get("answer") or ""
    print("[INFO] Réponse complète (answer):\n", answer)
    print("[INFO] Objet complet:\n", json.dumps(res, ensure_ascii=False, indent=2))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
