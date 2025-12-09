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

