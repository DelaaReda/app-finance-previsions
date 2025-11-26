# Finance Copilot — Dev & QA Discipline

## Principes non négociables
- Pas de mock, pas de fallback silencieux. En cas d’échec (API, modèle, data manquante), on logge et on remonte l’erreur de façon explicite.
- Données réelles uniquement (yfinance/FRED/news réelles/G4F premium). Une réponse vide ou inventée est interdite.
- Tests = simulation usage réel (LLM inclus), pas de tests “secs” hors données.
- Un problème non compris > une “rustine” silencieuse. On corrige la cause, pas le symptôme.

## Démarrage & environnement
- Toujours lancer via `./finance-copilot.sh start` (ne pas démarrer uvicorn/npm à la main).
- Backend: http://localhost:8050 – Frontend (si présent): http://localhost:5173.
- Env: `copilot-app/.env` (clé OpenRouter déjà présente, G4F no-auth). Pas de port custom.

## Sources de données
- Macro: `jobs/macro_series_snapshot.py` (FRED; fallback gold = yfinance GC=F déjà codé). Ajouts par défaut: CPI, VIX, DFF, UNRATE, 10y/2y, Michigan, DXY, WTI, Brent, Gold.
- Prix actions: yfinance live. Interdit d’utiliser un cache si le live échoue; mieux vaut retourner une erreur explicite.
- News: `news_ingest.py` + `news_sentiment.py` → pas de news factices. Limiter au top 5 scorées (recency × |sentiment|) côté judge.
- Features judge: `jobs/judge_enrich.py` (RSI, SMA spreads, vol20, momentum, drawdown, fundamentals yfinance).

## LLM & modèles
- `econ_llm_agent.py`: premium only (OpenRouter/DeepInfra/G4F power list). Pas de modèles “light” si les premium échouent; remonter l’erreur.
- Judge `/api/judge`: un seul appel LLM, timeout 120s (global 300s). Phases (fundamental/technical/macro/sentiment/fusion) incluses. `ml_prior` inclus ou `error` explicite.
- Tests LLM: `cd copilot-app/backend && PYTHONPATH=src .venv/bin/python scripts/test_judge_llm.py` (réel, pas de stub).

## Tests (réels, par étapes)
1) Rafraîchir données:
   - `PYTHONPATH=src .venv/bin/python jobs/macro_series_snapshot.py`
   - `PYTHONPATH=src .venv/bin/python jobs/news_ingest.py`
   - `PYTHONPATH=src .venv/bin/python jobs/news_sentiment.py`
   - `PYTHONPATH=src .venv/bin/python jobs/judge_enrich.py`
2) Tester LLM offline: `PYTHONPATH=src .venv/bin/python scripts/test_judge_llm.py`.
3) Tester API: `curl "http://localhost:8050/api/judge?limit=2"` et vérifier `phases`, `phase_scores`, `ml_prior`, `data_needed`.
4) En cas d’erreur, pas de fallback: corriger la source (clé API, réseau, data manquante).

## Payload judge (contrat attendu)
- features: enrichies (techniques, fondamentales), macro (avec deltas), news_count, phases, ml_prior (ou erreur explicite).
- news: top 5 scorées recency × |sentiment| (titre, sent, ts, source, résumé court, tickers).
- phases + phase_scores toujours présents si phases calculées.
- ml_prior: prédiction live yfinance-only; si indisponible, champ `error` explicite (pas de cache, pas de fallback).
- LLM: un seul appel premium, timeout 120s (global 300s), cite phase_scores, inclut data_needed si data manquante.

## Règles de dev backend
- Aucun fallback silencieux (prix, macro, news, LLM). Si une source échoue, lever/loguer et retourner l’erreur.
- Pas de données hardcodées pour “faire passer”. Préférer une erreur explicite à une réponse fausse.
- Logs explicites sur chaque fetch critique (data manquante, timeout modèle).
- Ne pas inventer de valeurs par défaut (0, []), sauf si le contrat l’exige et que c’est documenté.
- Toujours limiter les payloads LLM (top 5 news, features compactes), mais sans supprimer l’info critique.

## Revue & validation
- Vérifier que `ml_prior` n’est pas silencieusement absent : si baseline échoue, indiquer l’erreur.
- Vérifier que `phases` et `phase_scores` sont présents dans la réponse et cités par le LLM.
- Vérifier que les réponses incluent `data_needed` quand une donnée manque.
- Pas de commit si un test réel (steps ci-dessus) échoue ou si une donnée est simulée.

## Style de correction
- Causes réelles > contournements. On corrige la source (clé, réseau, parsing), pas le symptôme.
- Transparence: préférer une erreur claire qu’un résultat douteux.

## Check rapide avant livraison
- Scripts de rafraîchissement exécutés.
- `scripts/test_judge_llm.py` OK (réponse non vide, modèle premium).
- `curl /api/judge` OK (phases, phase_scores, ml_prior présent ou erreur explicite).
- Aucun fallback ou mock introduit.
