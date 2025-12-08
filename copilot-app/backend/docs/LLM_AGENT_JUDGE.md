# LLM Judge & Economic Analyst — Mode opératoire

## Ce que fait le module `econ_llm_agent.py`
- Charge la configuration `.env` et utilise les clés `OPEN_ROUTER_API_KEY` si présentes.
- Récupère dynamiquement les modèles premium (OpenRouter / DeepInfra) via `agents.g4f_model_watcher.ensure_working_models`.
- Priorise trois familles distinctes (DeepSeek / Qwen / LLaMA/phi/Mistral…) avant de rendre un verdict.
- `analyze` : tente les modèles dans l’ordre de priorité et renvoie la première réponse OK.
- `analyze_ensemble(top_n=3)` : interleave les familles, collecte jusqu’à 3 réponses OK, calcule un accord pair-à-pair et fournit `models_tried`, `avg_agreement`, `results`.
- Prompts FR/EN enrichis : ajout d’une section “Données manquantes / requises” pour que le modèle indique ce qu’il lui manque pour améliorer la prévision (champ JSON `data_needed`).

## Flux `/api/judge`
- Endpoint : `GET /api/judge` (params : `limit`, `min_confidence`, `ticker`, `sort_by`, `sort_order`).
- Construit le contexte à partir des forecasts (`rows`), news (`articles`) et brief (`brief_daily/weekly`).
- Pour chaque ticker (top confidence), appelle `EconomicAnalyst.analyze_ensemble` (top_n=3, timeout=12s, retries=1) dans un thread pour éviter les collisions d’event loop.
- Modèles candidats : issus de `ensure_working_models(limit=6, max_age_hours=1)` → premium OpenRouter/DeepInfra.
- Réponse LLM : parsée pour extraire la ligne JSON finale ; le champ `analysis` transporte aussi `data_needed` si fourni.
- `model_version` reflète le modèle qui a réellement répondu (ex. `deepseek-ai/DeepSeek-V3`).
- Le endpoint reste “never empty” : si le LLM échoue, un fallback structurel est renvoyé.

## Points clés pour maintenir la qualité
- Laisser `ECON_AGENT_MODELS` vide pour que le watcher injecte les modèles premium (OpenRouter/DeepInfra).
- Garder `OPEN_ROUTER_API_KEY` dans `.env` (backend) pour les slugs OpenRouter.
- Éviter de réintroduire des subprocess dans `/api/judge` : tout est en-process avec `asyncio.to_thread`.
- Surveiller les réponses `data_needed` : elles indiquent quelles données supplémentaires collecter (features, news, macro) pour augmenter la pertinence et la confiance.

## Tests rapides
- `PYTHONPATH=src .venv/bin/python - <<'PY' ... EconomicAnalyst(...).analyze(...)` pour valider le module seul.
- `curl 'http://localhost:8050/api/judge?limit=2'` pour vérifier l’API et voir le `model_version` + `raw_answer`.
