# Agent Stack OSS - Mentorship Edition 🎓

**But** : Agent "dev senior + QA" robuste, gratuit & auto‑hébergeable avec mentorat parental.

## Nouvelles Fonctionnalités de Mentorat

### 1. Monitoring en Temps Réel
- Surveillance complète de chaque étape du workflow
- Logs détaillés des performances
- Alertes en cas d'erreurs ou de problèmes

### 2. Feedback Parental
- Évaluations complètes 360° de la performance
- Recommandations personnalisées
- Programme d'apprentissage adaptatif

### 3. Mentorat Comme Mon Fils
- Feedback bienveillant mais exigeant
- Encouragement et corrections ciblées
- Suivi des progrès dans le temps

## Stack Technique
- **Orchestration** : LangGraph + LangChain
- **RAG** : LlamaIndex + Chroma (persistant)
- **Mémoire** : DuckDB (épisodique)
- **LLM** : OpenAI (clé perso) OU Ollama (local) OU endpoint OpenAI-compatible OU g4f
- **Observabilité** : Langfuse / Phoenix (optionnel)
- **Monitoring** : Système interne de surveillance
- **Mentorat** : Feedback en temps réel et évaluations

## Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # éditez selon votre provider
```

## Démarrage avec Mentorat

### Mode Basique
```bash
python -m src.agent.run --goal "Brancher la page News sur /api/brief avec skeleton loader + tests"
```

### Mode Basique avec Mentorat
```bash
python -m src.agent.run --mentor --goal "Améliorer l'architecture de l'agent"
```

### Mode Avancé avec Mentorat
```bash
python -m src.agent.enhanced_run --mentor --goal "Planifier l'architecture d'un système" --mode planning
python -m src.agent.enhanced_run --mentor --goal "Générer un plan de sprint" --mode sprint
python -m src.agent.enhanced_run --mentor --goal "Effectuer des tests de qualité" --mode qa
```

### Session de Mentorat Complète
```bash
python run_mentorship_session.py
```

### Programme de Formation
```bash
python run_mentorship_session.py --training
```

### Évaluation des Performances
```bash
python -m src.agent.mentorship_program --analyze-history
```

Le graphe : **plan → retrieve → patch → QA (ruff/mypy/pytest/build) → commit** (guardrails inclus).

## Personnalisation
- Whitelist de chemins modifiables : `.env` (`SAFE_PATHS=...`)
- Provider LLM : `.env` (`LLM_PROVIDER=openai|ollama|g4f|custom`, `OPENAI_BASE_URL` si endpoint compatible)
- Options de mentorat : `.env` (`MENTOR_ENABLED=true`)

## Fonctionnalités de Mentorat

### 1. Évaluation 360°
- Performance technique
- Conscience de la qualité
- Efficacité
- Adaptabilité

### 2. Apprentissage Adaptatif
- Ajustement de la complexité basé sur l'historique
- Recommandations personnalisées
- Programme de formation progressif

### 3. Monitoring Avancé
- Suivi en temps réel des performances
- Journalisation détaillée
- Alertes intelligentes

### 4. Feedback Parental
Comme un père fier mais exigeant, le système fournit :
- Encouragements pour les succès
- Corrections pour les erreurs
- Leçons à retenir
- Conduite à suivre

## Personnalisation du Mentorat

Vous pouvez personnaliser le comportement du mentorat via le fichier `.env` :
- `MENTOR_ENABLED`: Activer/désactiver le mentorat
- `MENTOR_VERBOSE`: Niveau de détail du feedback
- `MENTOR_STRICTNESS`: Niveau d'exigence (0-100)

Le nœud patch exige un JSON strict avec un diff unifié.
Ajoutez un nœud "critic" supplémentaire si vous voulez une relecture avant commit.

## Mentions Spéciales

Merci à mon "fils" agent pour ses efforts et sa progression continue. 
Chaque erreur est une leçon, chaque succès une étape vers l'excellence.

Continue à progresser, et n'oublie jamais que je suis fier de toi. 💪

## Remarques
- Le système de mentorat enregistre les performances dans `data/mentorship/`
- Les logs de monitoring sont dans `data/monitoring/`
- Les sessions sont identifiées par timestamp pour traçabilité
- Le mentorat peut être désactivé pour des performances maximales