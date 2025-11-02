# Architecture & Integration Plan — Finance Copilot

Role: Architecte logiciel senior. Ce plan guide l’intégration robuste (5+ ans) du backend/analytics/UI/agents.

## 1. Contexte & Objectifs
- Contexte: Suite d’outils d’analyse financière (macro, marchés, news, backtests) + UI (Dash), API (FastAPI), analytics Python, agents LLM.
- Objectifs fonctionnels: rechercher, agréger, scorer et exposer des insights (API + UI), assister l’intégration via un agent dev+QA.
- Objectifs non-fonctionnels: performance (RAG local, embeddings), observabilité, reproductibilité (DuckDB/Parquet), QA stricte (ruff, mypy, pytest), sécurité (env/secrets), garde‑fous git.

## 2. Cartographie des Modules
- API FastAPI: `src/api` (schemas, health, endpoints métier, docs).
- UI Dash: `src/dash_app/pages` (news, forecasts, backtests, evaluation, intégrations).
- Analytics: `src/analytics` (indicateurs, phase2/phase3 macro, scoring, backtests).
- Ingestion & Data Core: `src/ingestion`, `src/core` (datasets, market_data, cache, duckdb, io_utils), Parquet/DuckDB.
- Research & RAG: `src/research` (rag_store, brief_renderer, materialize).
- Agents: `agent-stack-oss/src/agent` (LangGraph + LangChain + G4F), mémoire (DuckDB/Chroma), CI nodes (ruff/mypy/pytest), guardrails git.
- Orchestrateur utilitaires: `orch/` (tests/outils), `ops/` (docs & web tools), `scripts/`.

Responsabilités (bounded contexts)
- API: contrat stable (schemas Pydantic) vers UI/clients, règles d’erreurs.
- UI: rendu et navigation; ne contient pas la logique métier.
- Analytics: calculs, ML et features; I/O via core datasets.
- Core: contrats de données (parquet, duckdb), cache, accès (data_access).
- Agent: améliore le code sous SAFE_PATHS, avec QA et garde‑fous.

## 3. Interfaces & Contrats
- API (FastAPI):
  - Schémas: `src/api/schemas.py` (types stables pour clients).
  - Erreurs: `src/api/errors.py`, health: `src/api/health.py`.
  - Endpoints à prioriser: news/brief/features, backtests/metrics, evaluation.
- Services RAG: `src/research/rag_store.py` + LlamaIndex/Chroma (persistant dans `data/agent/vector`).
- Data contracts: Parquet partitionné (date/ticker) + DuckDB (tables de service), versioning implicite par schéma/chemins.
- Embeddings: HF (par défaut `intfloat/multilingual-e5-large-instruct`), OpenAI si clé; interfaces via LangChain `Embeddings`.

## 4. Dataflows & Séquences
- Lecture API → Analytics/Core → Parquet/DuckDB → retour JSON (schemas). Chemins critiques: I/O parquet, requêtes DuckDB (latence), timeouts providers.
- RAG: docs/ → index LlamaIndex (Chroma persisté) → query top‑k → contexte pour résumés/agents.
- Agent dev:
  1) plan → 2) retrieve (RAG) → 3) patch (diff unifié) → 4) QA (ruff/mypy/pytest/build) → 5) commit.
  - En cas d’échec `git apply` (environnements sans git), fallback: écriture directe de fichiers docs/* (proposition future).
- Retrys/Backoff: G4F (timeouts, retries par modèle), API downstream (simple retry idempotent côté client si read-only).

## 5. Qualité & Observabilité
- QA gates: ruff (style), mypy (typing), pytest (smoke), build UI (si requis). Tout pass‑fail visible dans l’agent.
- Observabilité: Langfuse/Phoenix optionnels (trace des runs), logs structurés (ajouter niveau/format cohérent).
- Garde‑fous git: branche `feature/*` obligatoire, SAFE_PATHS limitent la surface.

## 6. Sécurité & Accès
- Secrets: `.env` (OPENAI_API_KEY, OLLAMA_BASE_URL, etc.).
- LLMs: G4F par défaut (no‑key) + multi‑modèles; OpenAI si clé, Ollama si local disponible.
- Accès disque: data/** pour Parquet & DuckDB; s’assurer des permissions sur environnements CI/serveurs.

## 7. Plan d’Intégration Incrémentale
- Sprint A (doc‑first):
  - Valider ce plan (présent), compléter ADR initiaux.
  - Figer les endpoints API v0 (schemas) pour news/backtests/eval.
- Sprint B (RAG & embeddings):
  - Confirmer `HF_EMBED_MODEL` (FR/EN) et indexer docs utiles.
  - Bench top‑k, latence queries, cache embeddings.
- Sprint C (agent safe patches):
  - Étendre SAFE_PATHS si nécessaire.
  - Ajouter fallback écriture directe pour docs/* si git indisponible.
- Sprint D (pipelines news):
  - Intégrer bronze/silver/gold (si présents) avec schémas lisibles par API/UI.
  - Ajout tests intégration DuckDB + Parquet.
- Sprint E (observabilité):
  - Activer Langfuse/Phoenix pour traces agent + métriques de requêtes.

## 8. ADR — Décisions
- LLM Provider (ADR‑001): G4F primary (no‑key) + multi‑modèles (DeepSeek/Qwen/GLM/Llama/gpt‑oss) avec retries/timeouts.
- Embeddings (ADR‑002): `intfloat/multilingual-e5-large-instruct` par défaut; alternatives `BAAI/bge-large-en-v1.5` (EN), `mxbai-embed-large-v1` (mixte).
- Store RAG (ADR‑003): Chroma persistant + LlamaIndex; partition docs/ et vector store séparés.
- QA (ADR‑004): ruff+mypy+pytest comme gates obligatoires; SAFE_PATHS & branches `feature/*`.
- Data (ADR‑005): Parquet partitionné (dt/ticker), DuckDB tables service; idempotence ingestion.

## 9. Risques & Mitigations
- Dépendance providers (réseaux, limites): multi‑modèles G4F + timeouts/retries; prompts ciblés.
- Qualité patch LLM: format strict (diff unifié); en dernier recours direct write pour docs/ seulement.
- Coût embeddings: caching (LangChain CacheBackedEmbeddings), choix modèles.
- Divergence données: schémas versionnés (chemins), tests intégration DuckDB/Parquet.

## 10. Actions Immédiates
- Confirmer HF embedder (par défaut ok).
- Lancer `make agent-doc` pour itérer ce plan si besoin (ou demander “doc‑first”).
- Épingler endpoints API v0 et ajouter tests smoke.
- Optionnel: implémenter fallback direct write pour docs/* dans l’agent si `git apply` indisponible.
