# JUDGE_SCHEMA – Décembre 2025

Vue contractuelle du retour `/api/judge` (verdict typé unique) et du builder associé.

## 1) Où vit la logique ?
- **Pipeline métier** (`judge.py` + jobs) : calcule expected_return(_ensemble/_raw), phases, features, news, ml_prior.  
- **Builder typé** (`services/judge_builder.py`) : normalise et mappe vers `JudgeVerdict` (schemas/judge.py).  
- **Route** (`api/routes/judge.py`) : ne garde qu’une seule liste pour le front (`data.verdicts`), et ajoute `verdicts_raw` uniquement si `debug=true`.

## 2) Contrat API (résumé)
- `data.verdicts` : liste de `JudgeVerdict` **typés** (front consomme ça).  
- `data.verdicts_raw` : uniquement en `debug=true` (trace du payload brut).  
- Scores de phase :  
  - `phase_scores` : normalisés 0–1 (sentiment normalisé si >1 → /100).  
  - `phase_scores_raw` : version brute (ex. sentiment 74.2) conservée pour debug.  
- Scénarios : probabilités normalisées 0–1 (si le LLM renvoie 60 → 0.6).  
- `ml_prior` du pipeline écrase celui du LLM si présent.

## 3) Schéma `JudgeVerdict` (principal)
- `ticker`, `horizon`, `direction` (dérivée d’expected_return).  
- `expected_return`, `expected_return_ensemble`, `expected_return_raw`.  
- `risk_level` (low/medium/high).  
- `confidence`, `quant_confidence` (ml_prior.confidence si dispo).  
- `summary`, `scenarios[]`, `risks`, `impacts`, `actions`, `data_needed`.  
- `phase_scores` (0–1), `phase_scores_raw` (optionnel), `phases{fundamental|technical|macro|sentiment|fusion}`.  
- `ml_prior`, `attachments` (news compact), `meta{generated_at, model_version, provider, profile, source}`.  
- `raw_answer`, `debug_payload`, `debug_llm_res` conservés pour debug.

## 4) Tests & usage
- **Local** : `curl "http://localhost:8050/api/judge?limit=1&debug=true"`  
  - `data.verdicts` : structure typée (frontend).  
  - `data.verdicts_raw` : payload brut (debug).  
- **Schema** : cf. `schemas/judge.py` (Pydantic v1/v2 compat. + shim si pydantic absent).  
- **Builder** : `services/judge_builder.py` (utilisé par la route ; à modifier si on change le contrat de sortie, pas ailleurs).

## 5) Règles de maintenance
- Changement **métier** (scores, features) → pipeline/jobs.  
- Changement **forme/contrat** (noms de champs, normalisation) → `judge_builder.py` + `schemas/judge.py`.  
- Éviter les champs dupliqués : la liste finale est toujours typée ; le brut reste en debug uniquement.  

---

## 6) Flow complet `/api/judge` (réutilisable pour d’autres endpoints)

1. **Données d’entrée (fichiers/cache)**
   - `data/forecasts.json` : expected_return_raw, direction, confidence brute.
   - `data/judge_features.json` : enrichissements tech/fundamentals (jobs/judge_enrich.py).
   - `data/macro_series.json` : snapshot macro (FRED + fallback yfinance).
   - `data/news_feed.json` : news normalisées (jobs/news_ingest.py + news_sentiment.py).
   - `brief_daily/weekly` : signaux/risk composites (optionnel).

2. **Assemblage pipeline (judge.py)**
   - Charge profil (`data/judge_profiles/*.yaml`) : tickers, max_tokens, focus, prompt_template.
   - Construit features : tech/macro/news/ownership/ml_prior + phases (fundamental/technical/macro/sentiment/fusion) via `analytics.phases_adapter`.
   - Calcule expected_return_ensemble (mix forecast + ml_prior).
   - Prépare payload LLM (question + features + phases + news top 5).

3. **Appel LLM**
   - Client principal : Codestral/OpenRouter (fallback G4F désactivé si pas de modèles testés).
   - Réponse attendue : JSON strict (summary, scenarios, risks, impacts, actions, confidence, data_needed, phase_scores, ml_prior).
   - Audit/repair : Groq qwen3-32b tente de réparer le JSON en cas d’échec parse.
   - Normalisation interne : phase_scores list → dict, sentiment >1 → /100, clamp 0–1.

4. **Filtrage et stats**
   - Tri par confidence/expected_return/score/risk_level/timestamp.
   - Filtre min_confidence (par défaut 0.3) ; si vide et erreurs LLM, renvoie quand même pour debug.
   - Stats : total_verdicts, high_confidence_count (>=0.7), avg_confidence.

5. **Construction finale**
   - Builder typé : `services/judge_builder.build_judge_verdict` → `schemas/judge.JudgeVerdict`.
   - `data.verdicts` : version typée unique pour le front.
   - `data.verdicts_raw` : uniquement en `debug=true` pour inspection.
   - `debug_pipeline` : traces étape par étape (data_loaded, phases_built, llm_call, row_done…).

6. **Test / Smoke**
   - `curl "http://localhost:8050/api/judge?limit=1&debug=true"` : vérifie parsing + phase_scores normalisés.
   - Hook pre-push exécute `scripts/smoke.sh` (ping /api/judge) après santé backend.

7. **Réutilisation pour d’autres endpoints**
   - Garder la séparation :
     - Calcul métier (features, scores, aggregation) dans le pipeline concerné.
     - Mapping/normalisation → nouveau builder Pydantic dédié (copier le pattern `judge_builder.py`).
   - Toujours une seule liste “canonique” pour le front ; garder le brut seulement en debug.
   - Normaliser les échelles (0–1) côté builder ; conserver les raw uniquement pour diagnostic.

8. **Gestion erreurs / données manquantes**
   - Pas de mocks : si data manquante → laisser vide et lister dans `data_needed`.
   - LLM JSON invalide → tentative de réparation Groq sinon fallback minimal texte + parse error en debug.
   - News sources en échec : log + (optionnel) inscrire la source manquante dans meta pour le LLM.
