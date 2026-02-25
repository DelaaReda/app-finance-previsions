# Epics MVP — orientées exécution agents qwen

## EPIC A — Stabiliser les contrats API MVP

### Objectif
Garantir des réponses cohérentes, testables et stables sur les 5 endpoints MVP.

### Scope IN
- Normalisation payload succès/erreur
- Vérification de la cohérence route vs router (`/api/forecasts`)
- Ajout/renforcement tests backend ciblés MVP

### Scope OUT
- Refonte complète architecture backend
- Ajout de nouvelles familles d’endpoints non MVP

### Prérequis
- Backend local démarrable (`./finance-copilot.sh restart`)
- `.venv` backend opérationnel

### Fichiers cibles
- `copilot-app/backend/src/api/main.py`
- `copilot-app/backend/src/api/routes/forecasts.py`
- `copilot-app/backend/tests/test_health.py`
- `copilot-app/backend/tests/` (nouveaux tests endpoint)

### Dépendances
- EPIC C (quality gate) pour verrouillage final

### Risques
- Régressions liées aux fallbacks historiques
- Variabilité des données snapshots

### Critères d’acceptation testables
1. Les 5 endpoints MVP retournent HTTP 200 en mode nominal.
2. Chaque endpoint retourne un objet top-level avec `ok` + charge utile structurée.
3. Pas d’erreur 500 sur 10 appels successifs à chaque endpoint.
4. Tests backend MVP passent en local.

### Commandes de test
```bash
curl -sS http://localhost:8050/api/health | jq
curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq
curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq
curl -sS "http://localhost:8050/api/forecasts" | jq
curl -sS -X POST "http://localhost:8050/api/copilot/ask" -H 'Content-Type: application/json' \
  -d '{"question":"Vue rapide du marché","max_sources":3}' | jq
cd copilot-app/backend && .venv/bin/pytest -q
```

### Evidences attendues
- Sorties `curl|jq` sauvegardables
- Log `api.log` sans tracebacks critiques
- Rapport pytest vert

---

## EPIC B — Intégrer le frontend MVP avec données réelles

### Objectif
Rendre l’UI MVP utilisable sans dépendre implicitement des mocks.

### Scope IN
- Brancher vues clés sur endpoints MVP
- Afficher explicitement fallback « Données simulées »
- États erreur/empty robustes côté UI

### Scope OUT
- Refonte UX complète de l’application
- Nouveau design system

### Prérequis
- EPIC A partiellement livré (contrats API minimum stables)
- Frontend statique servi sur `:5173`

### Fichiers cibles
- `copilot-app/frontend/app/app.js`
- `copilot-app/frontend/app/mockData.js`
- `copilot-app/frontend/app/index.html`
- `copilot-app/frontend/app/style.css`

### Dépendances
- EPIC A (contrat API)
- EPIC C (tests smoke navigateur)

### Risques
- Couplage fort logique UI legacy + contenu mock massif
- Régression de navigation hub (diamond)

### Critères d’acceptation testables
1. Les sections MVP affichent des données API en priorité.
2. Si fallback mock activé, badge visible et non ambigu.
3. Aucune erreur JS bloquante en console sur parcours MVP.
4. Le parcours principal (ouvrir app, charger data, consulter prévisions/news) fonctionne.

### Commandes de test
```bash
./finance-copilot.sh restart
# Vérif manuelle: http://localhost:5173
# Vérif console browser: aucune erreur bloquante
```

### Evidences attendues
- Captures d’écran des sections MVP
- Extraits console (0 erreurs bloquantes)
- Journal des appels réseau (200 sur endpoints MVP)

---

## EPIC C — Industrialiser qualité et exécution multi-agents qwen

### Objectif
Rendre l’exécution des stories reproductible via qwen orchestrator avec preuves systématiques.

### Scope IN
- Templates de dispatch story/tâche
- Quality gate compact backend + frontend
- Convention d’artefacts de preuves

### Scope OUT
- CI/CD cloud complet
- Observabilité SRE avancée

### Prérequis
- `scripts/qwen_orchestrator.py` opérationnel
- Rôles tmux/agent disponibles (planner/dev/tester/qa)

### Fichiers cibles
- `scripts/qwen_orchestrator.py` (si ajustements prompts/guardrails)
- `scripts/analyze_orchestrator_runs.py`
- `finance-app/openclaw-gates/` (artefacts)
- `docs/planning/*.md`

### Dépendances
- EPIC A/B pour valider gates sur vrai périmètre

### Risques
- Dérive de scope des agents
- Preuves incomplètes ou non auditables

### Critères d’acceptation testables
1. Chaque story exécutée produit un bloc: DELTA, EVIDENCE, RISKS, NEXT.
2. Un gate unique donne verdict PASS/BLOCKED pour le MVP.
3. Les artefacts de run sont traçables par run_id horodaté.

### Commandes de test
```bash
python3 scripts/qwen_orchestrator.py --tmux-cmd status
python3 scripts/analyze_orchestrator_runs.py --runs-dir finance-app/orchestrator-runs --limit 5
```

### Evidences attendues
- `finance-app/orchestrator-runs/<run_id>/transcript.md`
- `events.jsonl` + `agent_activity.json`
- Rapport gate dans `finance-app/openclaw-gates/`
