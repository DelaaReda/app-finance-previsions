# User Stories MVP (détaillées)

## Story A1 — Contrat santé & observabilité minimale

- **Objectif**: fiabiliser `/api/health` comme source de vérité runtime.
- **Scope IN**: structure réponse stable, champs minimum (`ok`, `status`, `data.timestamp`, `data.last_updates`).
- **Scope OUT**: observabilité avancée (traces distribuées, métriques infra).
- **Prérequis**: backend démarre localement.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/tests/test_health.py`
- **Plan implémentation**:
  1. Formaliser shape unique de réponse health.
  2. Supprimer ambiguïtés (`status` top-level vs `data.status`) si nécessaire via compat contrôlée.
  3. Ajouter tests de contrat.
- **Critères d’acceptation testables**:
  - `GET /api/health` retourne 200 et `ok=true`.
  - `data.last_updates` existe (objet, vide autorisé).
  - Test dédié passe en local.
- **Commandes de test**:
  - `curl -sS http://localhost:8050/api/health | jq`
  - `cd copilot-app/backend && .venv/bin/pytest -q tests/test_health.py`
- **Evidences attendues**: sortie curl + test vert.
- **Risques**: clients historiques dépendants d’anciens champs.
- **Dépendances**: aucune.

---

## Story A2 — Normaliser `/api/stocks/prices`

- **Objectif**: unifier les réponses mono/multi ticker sans surprise côté UI.
- **Scope IN**: shape explicite, erreurs paramètre claires, downsample robuste.
- **Scope OUT**: nouvelle source de marché externe.
- **Prérequis**: snapshots prix disponibles ou fallback fonctionnel.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/core/downsample.py`
  - `copilot-app/backend/tests/` (nouveau test stocks)
- **Plan implémentation**:
  1. Documenter contrat mono ticker et multi ticker.
  2. Ajouter test paramétrique pour `ticker` vs `tickers`.
  3. Vérifier gestion absence data.
- **Critères d’acceptation testables**:
  - Mono ticker: payload contient `ticker`, `points`, `count`.
  - Multi ticker: payload contient `tickers` map.
  - Requête invalide renvoie `ok=true` + message d’erreur contrôlé (pas 500).
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq`
  - `curl -sS "http://localhost:8050/api/stocks/prices?tickers=SPY&tickers=QQQ" | jq`
- **Evidences attendues**: exemples de payload mono/multi.
- **Risques**: incohérence historique de schéma côté frontend.
- **Dépendances**: Story B1.

---

## Story A3 — Normaliser `/api/news/feed`

- **Objectif**: garantir liste d’articles exploitable avec métadonnées minimales.
- **Scope IN**: normalisation `title/url/published_at/source/tickers/score`, limite, fallback.
- **Scope OUT**: moteur de ranking news avancé.
- **Prérequis**: `news_feed.json` accessible ou service news actif.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/api/services/news_service.py`
  - `copilot-app/backend/tests/` (nouveau test news)
- **Plan implémentation**:
  1. Fixer format final `items` (+ alias `articles` compat).
  2. Tester filtrage `tickers`, `limit`.
  3. Valider comportement never-empty contrôlé.
- **Critères d’acceptation testables**:
  - `count` cohérent avec items renvoyés.
  - Chaque item a `title` et `url` (vides tolérés mais clé présente).
  - Aucun 500 en absence de news.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/news/feed?limit=5" | jq`
  - `curl -sS "http://localhost:8050/api/news/feed?tickers=AAPL&limit=5" | jq`
- **Evidences attendues**: payload normalisé + test automatisé.
- **Risques**: qualité variable des sources upstream.
- **Dépendances**: Story C1.

---

## Story A4 — Route `/api/forecasts` unique et stable

- **Objectif**: éviter conflit route commentée/main vs router dédié.
- **Scope IN**: confirmer source de vérité `api/routes/forecasts.py`, contrat de sortie stable.
- **Scope OUT**: refonte modèle de prévision.
- **Prérequis**: router forecasts importé au boot.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/routes/forecasts.py`
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/tests/` (nouveau test forecasts)
- **Plan implémentation**:
  1. Vérifier branchement router et tags.
  2. Standardiser champs réponse (`rows/items/count/source`).
  3. Ajouter test de contrat.
- **Critères d’acceptation testables**:
  - `GET /api/forecasts` renvoie 200 en local.
  - Contrat stable documenté dans test.
- **Commandes de test**:
  - `curl -sS "http://localhost:8050/api/forecasts" | jq`
- **Evidences attendues**: preuve endpoint + test passe.
- **Risques**: doublons logiques legacy.
- **Dépendances**: Story A1.

---

## Story A5 — Durcir `/api/copilot/ask`

- **Objectif**: réponse robuste même sans sources RAG ou sans LLM configuré.
- **Scope IN**: validations input, erreurs contrôlées, métadonnées qualité.
- **Scope OUT**: amélioration profonde du moteur RAG.
- **Prérequis**: modules `research.rag_store` et `research.llm_client` importables.
- **Fichiers cibles**:
  - `copilot-app/backend/src/api/main.py`
  - `copilot-app/backend/src/research/llm_client.py`
  - `copilot-app/backend/tests/` (nouveau test copilot ask)
- **Plan implémentation**:
  1. Encadrer les exceptions avec messages actionnables.
  2. Garantir présence `answer`, `sources`, `confidence`.
  3. Ajouter tests cas nominal + cas sans sources.
- **Critères d’acceptation testables**:
  - POST valide retourne `ok=true` + `answer` string.
  - Cas sans source n’explose pas.
- **Commandes de test**:
  - `curl -sS -X POST "http://localhost:8050/api/copilot/ask" -H 'Content-Type: application/json' -d '{"question":"TL;DR marché","max_sources":3}' | jq`
- **Evidences attendues**: payload incluant `sources_count`/`quality_status`.
- **Risques**: dépendances externes LLM indisponibles.
- **Dépendances**: Story C1.

---

## Story B1 — Wiring frontend des vues MVP vers API

- **Objectif**: brancher sections clés UI sur endpoints réels.
- **Scope IN**: appels fetch MVP, mapping payload vers UI, loading states.
- **Scope OUT**: refonte totale `app.js`.
- **Prérequis**: Stories A1–A4 stabilisées.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/index.html`
- **Plan implémentation**:
  1. Créer couche d’accès API minimale (helpers fetch).
  2. Mapper réponses health/news/forecasts/stocks.
  3. Garder fallback mock seulement en dernier recours.
- **Critères d’acceptation testables**:
  - Chargement initial déclenche appels réseau API.
  - Données affichées sans crash JS.
- **Commandes de test**:
  - Ouvrir `http://localhost:5173` puis vérifier onglets MVP.
- **Evidences attendues**: capture réseau + screenshot sections remplies.
- **Risques**: dette technique importante dans `app.js`.
- **Dépendances**: EPIC A.

---

## Story B2 — Badge fallback simulé + gestion erreurs UI

- **Objectif**: rendre visible l’usage de mocks et éviter confusion utilisateur.
- **Scope IN**: badge `Données simulées`, messaging erreur/empty.
- **Scope OUT**: redesign complet composants.
- **Prérequis**: B1 branchée.
- **Fichiers cibles**:
  - `copilot-app/frontend/app/app.js`
  - `copilot-app/frontend/app/style.css`
  - `copilot-app/frontend/app/mockData.js`
- **Plan implémentation**:
  1. Détecter origine donnée (api/mock).
  2. Afficher badge sur widgets concernés.
  3. Normaliser messages erreur.
- **Critères d’acceptation testables**:
  - En mode fallback, badge visible.
  - En mode API, badge absent.
- **Commandes de test**:
  - Test manuel navigateur (mode API dispo / indispo).
- **Evidences attendues**: deux captures (API réel vs fallback).
- **Risques**: détection source incomplète selon modules.
- **Dépendances**: B1.

---

## Queue de stories (delta incrémental)

- **RUN_NOW**: Story A1, Story A2
- **RUN_NEXT_IF_PASS**: Story A3
- **ON_HOLD**: Story B1, Story B2 (attente lock contrats API)
- **PARALLEL_PREP**: Story C1 (template de rapport + structure d’artefacts)

## Cartes de dispatch stories (delta 20:05)

### Dispatch Card — Story A1 (à envoyer au planner/dev/tester)
- Objectif: figer un contrat health rétro-compatible
- In: shape stable + test dédié
- Out: observabilité avancée
- Vérifications obligatoires: curl health + pytest test_health
- Evidence minimale: JSON réponse + sortie pytest + verdict PASS/BLOCKED

### Dispatch Card — Story A2 (à envoyer après A1 dans le même lot)
- Objectif: rendre le contrat mono ticker exploitable UI
- In: ticker/points/count/timestamp + absence de 500
- Out: multi-ticker et perf
- Vérifications obligatoires: curl SPY + 5 appels consécutifs sans 500
- Evidence minimale: payload SPY + trace boucle + verdict PASS/BLOCKED

## Story C1 — Gate de régression MVP compact

- **Objectif**: créer un gate simple PASS/BLOCKED avant livraison.
- **Scope IN**: health + 5 endpoints + smoke + sanity frontend.
- **Scope OUT**: suite E2E exhaustive.
- **Prérequis**: stories A/B principales intégrées.
- **Fichiers cibles**:
  - `skills/finance-regression-gate/` (si enrichissement)
  - `finance-app/openclaw-gates/`
  - `docs/planning/tasks.md` (matrice run)
- **Plan implémentation**:
  1. Définir checklist exécutable unique.
  2. Produire rapport horodaté (markdown/json).
  3. Marquer PASS/BLOCKED avec causes.
- **Critères d’acceptation testables**:
  - Gate produit un verdict unique et actionnable.
  - Rapport contient commandes + résultats + anomalies.
- **Commandes de test**:
  - `./finance-copilot.sh restart`
  - `./scripts/smoke.sh`
  - commandes `curl` MVP
- **Evidences attendues**: fichier de gate + logs de commandes.
- **Risques**: faux positifs si données snapshots périmées.
- **Dépendances**: A1..A5, B1..B2.

## Delta stories prêtes qwen (cycle 20:20)

### Story A1 — compléments d’acceptation qwen
- **Critère ajouté**: exécuter 3 appels consécutifs health sans variation de schéma.
- **Evidence attendue ajoutée**: extrait compact des 3 réponses + timestamp run.

### Story A2 — compléments d’acceptation qwen
- **Critère ajouté**: boucle 5x sur `ticker=SPY` sans 500 ni clé manquante.
- **Evidence attendue ajoutée**: tableau texte `run_i -> status_code -> keys_present`.

### Story A3 (RUN_NEXT_IF_PASS)
- **Précondition renforcée**: ne démarre que si artefact Batch-01 contient un verdict PASS signé QA.

## Delta dispatch prêt agents qwen (cycle 20:35)

### Story A1 — brief agent exécutable
- **Rôle principal**: dev
- **Rôles support**: tester, qa
- **Commande de preuve obligatoire**:
  - `for i in {1..3}; do curl -sS http://localhost:8050/api/health | jq -c '{ok,status,ts:.data.timestamp}'; done`
- **Condition DONE**: 3 réponses cohérentes + test health vert + verdict QA PASS

### Story A2 — brief agent exécutable
- **Rôle principal**: dev
- **Rôles support**: tester, qa
- **Commande de preuve obligatoire**:
  - `for i in {1..5}; do curl -sS "http://localhost:8050/api/stocks/prices?ticker=SPY" | jq -c '{ok,ticker,count,has_points:(.data.points!=null),has_ts:(.data.timestamp!=null)}'; done`
- **Condition DONE**: 5 réponses sans 500 + clés présentes + verdict QA PASS

### Story A3 — carte de reprise conditionnelle
- **Activation**: uniquement après artefact Batch-01 avec `VERDICT: PASS`
- **Préparation autorisée**: cadrage test contract `items/count` + alias `articles`

## Delta stories (cycle 20:50)

### Story A2 (Batch-02 prep) — extension conditionnelle
- **Activation**: après `VERDICT: PASS` de Batch-01.
- **Objectif additionnel**: verrouiller contrat multi-ticker via tests formels (`T-A2.2`).
- **Acceptance additionnelle**:
  - réponse multi ticker avec map stable
  - test dédié vert, sans 500 sur input incomplet

### Story A3 (Batch-02 prep) — carte exécutable
- **Activation**: enchaînée à A2.2 dans le même lot conditionnel.
- **Scope IN**: normalisation `items/count` + alias `articles`.
- **Evidence minimale**:
  - payload `news/feed` normalisé
  - preuve test ou check contract

### Ordre imposé en Batch-02
1. Story A2 (multi-ticker contract)
2. Story A3 (news contract)
3. QA signe `PASS|BLOCKED` pour le lot

## Changelog
- 2026-02-24 19:50 America/New_York — Ajout d’une queue de stories incrémentale (RUN_NOW/RUN_NEXT/ON_HOLD/PARALLEL_PREP) pour guider le dispatch qwen sans redémarrer le cadrage.
- 2026-02-24 20:05 America/New_York — Ajout de cartes de dispatch prêtes à l’envoi pour Story A1/A2 (objectif, scope, vérifications, preuves minimales).
- 2026-02-24 20:20 America/New_York — Durcissement incrémental des stories A1/A2 (stabilité multi-appels et preuves structurées) + précondition QA explicite avant ouverture Story A3.
- 2026-02-24 20:35 America/New_York — Ajout d’un brief de dispatch exécutable pour A1/A2 (rôles + commandes de preuve obligatoires) et carte de reprise A3 strictement conditionnée au verdict PASS Batch-01.
- 2026-02-24 20:50 America/New_York — Préparation incrémentale de Batch-02: ordre imposé Story A2->A3, critères additionnels multi-ticker/news et preuves minimales pour signature QA.
