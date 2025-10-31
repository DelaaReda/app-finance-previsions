
# OSS Senior Dev + QA Agent (LangGraph + LangChain + LlamaIndex + Chroma + DuckDB)
**But** : Agent “dev senior + QA” robuste, gratuit & auto‑hébergeable.
## Stack
- **Orchestration** : LangGraph + LangChain
- **RAG** : LlamaIndex + Chroma (persistant)
- **Mémoire** : DuckDB (épisodique)
- **LLM** : OpenAI (clé perso) OU Ollama (local) OU endpoint OpenAI-compatible OU g4f
- **Observabilité (optionnel)** : Langfuse / Phoenix
## Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # éditez selon votre provider
```
## Démarrage
- Placez quelques docs dans `./docs` pour le RAG.
- Assurez-vous d’être sur une branche `feature/*` (pas `local-branch`) dans votre repo git.
```bash
python -m src.agent.run --goal "Brancher la page News sur /api/brief avec skeleton loader + tests"
```
Le graphe : **plan → retrieve → patch → QA (ruff/mypy/pytest/build) → commit** (guardrails inclus).
## Personnalisation
- Whitelist de chemins modifiables : `.env` (`SAFE_PATHS=...`)
- Provider LLM : `.env` (`LLM_PROVIDER=openai|ollama|g4f|custom`, `OPENAI_BASE_URL` si endpoint compatible)
## Remarques
- Le nœud patch exige un JSON strict avec un diff unifié.
- Ajoutez un nœud “critic” supplémentaire si vous voulez une relecture avant commit.
