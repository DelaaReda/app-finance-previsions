# Architecture & Integration Plan (Template)

Role: Architecte logiciel senior. Ce document sert de base avant toute modification de code.

## 1. Contexte & Objectifs
- Contexte du produit / domaine
- Objectifs fonctionnels (features) et non-fonctionnels (perf, observabilité, sécurité)

## 2. Cartographie des Modules
- Modules actuels (api, analytics, ingestion, research, ui)
- Responsabilités et limites (Bounded Contexts)
- Dépendances explicites

## 3. Interfaces & Contrats
- APIs internes (signatures, schémas, erreurs)
- Événements / messages (topics, payloads, idempotence)
- Contrats de données (parquet/duckdb, versioning, partitionnement)

## 4. Dataflow & Séquences
- Diagrammes (synchrones / asynchrones)
- Chemins critiques et points d’échec
- Politique de retries / backoff

## 5. Qualité & Observabilité
- QA gates: ruff, mypy, pytest, builds UI
- Logs, métriques, traces (Langfuse/Phoenix si activé)

## 6. Sécurité & Accès
- Secrets (env), clés providers (g4f, openai), permissions
- Mécanismes de sandbox / guardrails git (branches autorisées, safe paths)

## 7. Plan d’Intégration Incrémentale
- Milestones (itérations), critères de done
- Stratégie de migration (feature flags, A/B, rollback)

## 8. ADR — Décisions
- Choix des LLMs (G4F models: DeepSeek/Qwen/GLM/Llama/gpt-oss) et rationales
- Embeddings: `intfloat/multilingual-e5-large-instruct` par défaut (multilingue, qualité)
- RAG: Chroma + LlamaIndex, index persistant, cache embeddings

## 9. Risques & Mitigations
- Dépendances externes (modèles, réseaux)
- Qualité des patchs LLM (diff unifié strict) → post-critique/validator

## 10. Actions Immédiates
- Décrire le premier lot de tâches (doc → smoke → patch minimal → QA)

