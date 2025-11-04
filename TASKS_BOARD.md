# 📣 MESSAGE AUX AGENTS — Lisez-moi et démarrez

Équipe, bienvenue dans **Finance Copilot**.
Ici on livre **du vrai**: zéro mock, zéro “quick fix” qui masque les problèmes.
Votre mission: **rendre l’app stable, rapide et alimentée par de la vraie data**.

---

## 0) Règles d’or (obligatoires)

1. **Démarrage/arrêt uniquement via le script**

```bash
/Users/venom/Documents/analyse-financiere/finance-copilot.sh start
/Users/venom/Documents/analyse-financiere/finance-copilot.sh stop
/Users/venom/Documents/analyse-financiere/finance-copilot.sh status
```

2. **Ports standard**: Front `5173`, Back `8050`. Ne changez pas.

3. **Never-Empty**: toute API sert **le dernier snapshot valide** + métadonnées de fraîcheur.

4. **Zéro mock**: si une route est vide, vous implémentez ingestion/pipeline/cache. Point.

5. **UI incassable**: un tableau vide n’est pas une erreur; un `.map` sur `undefined` oui.
   Protégez systématiquement `data?.items ?? []` et affichez un état vide propre.

6. **No PR**: on travaille en **commit direct**, **petits lots**, **clair et atomique**.

7. **Locks anti-collision**: une tâche = un fichier lock `.locks/<TASK-ID>.lock`.
   Le premier qui pousse le lock a la tâche.

8. **Preuve avant push**: exécutez le smoke test et joignez une preuve (capture/log/curl).

---

## 1) Comment prendre une tâche (process clair)

### a) Claimer la tâche

```bash
echo "owner=@<handle>
when=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > .locks/FC-P0-001.lock

git add .locks/FC-P0-001.lock TASKS_BOARD.md
git commit -m "claim: FC-P0-001 by @<handle>"
git push
```

* Si le lock existe déjà → la tâche est prise. Choisissez-en une autre.
* Mettez la tâche en **CLAIMED** dans `TASKS_BOARD.md` avec votre @handle.

### b) Livrer

* Ne modifiez que les fichiers nécessaires.
* Ajoutez vos **preuves** dans `proofs/<TASK-ID>/<handle>/`.
* Mettez à jour votre score dans `SCORE_AGENTS.md` (si applicable).

### c) Vérifier puis pousser

* Lancez le **smoke test** (voir plus bas).
* Passez la tâche en **DONE** dans `TASKS_BOARD.md`.
* Supprimez le lock dans le même commit.

```bash
git add <fichiers_changés> proofs/FC-P0-001/<handle>/* SCORE_AGENTS.md TASKS_BOARD.md
git commit -m "done: FC-P0-001 – <résumé bref> (+<points>)"
git rm .locks/FC-P0-001.lock
git push
```

**Règle “commit clair”**: pas de `git add -A`. Ajoutez **uniquement** ce que vous avez touché.

---

## 2) Plan d’intégration (commun à toutes les tâches)

### Backend (FastAPI)

* **Storage minimal**: ajoutez une couche disque (json/parquet) pour chaque domaine: `forecasts`, `news`, `briefs`, `backtests`, `macro`.
* **Cache fonctionnel**: implémentez un `load_or_compute(key, compute_fn)`:

  * charge `key.json` si présent → renvoie immédiatement (never-empty)
  * sinon **calcule réellement** (ingestion/pipeline), puis **sauvegarde** et renvoie
* **Scheduler**: mettez en place des jobs pour pré-calculer:

  * `news` toutes les 15 min
  * `forecasts` quotidien (ou sur demande)
  * `brief_weekly` hebdo (pré-calcul pour réponse instantanée)
  * `backtests` quand de nouvelles prévisions sont prêtes
* **Contrats stables**: chaque endpoint expose un schéma documenté (sections “DoD” ci-dessous).

### Frontend (React/Vite)

* **Sélecteurs sûrs**: utilisez `const rows = data?.rows ?? []` et équivalents.
* **Empty-state propre**: affichez un message clair, une date de fraîcheur, pas de stacktrace.
* **ErrorBoundary global**: une erreur affichée n’est pas une UX.
* **Freshness badge**: la vue indique “Dernière mise à jour: <date> • statut: fresh/stale”.

### Observabilité & DX

* **Smoke test** local: un script qui ping les routes critiques et checke des clés attendues.
* **Logs clairs**: loggez la durée des compute, la source de data, l’état du cache.

---

## 3) Smoke test (à exécuter avant chaque push)

```bash
# backend doit tourner via finance-copilot.sh
curl -sS http://localhost:8050/api/health | grep -i ok
curl -sS http://localhost:8050/api/news/feed | grep -i articles
curl -sS http://localhost:8050/api/forecasts | grep -i rows
curl -sS http://localhost:8050/api/brief/weekly | head -c 200
curl -sS http://localhost:8050/api/backtests | head -c 200
```

* Si l’un échoue → **corrigez avant push**.
* Ajoutez une capture du résultat dans `proofs/<TASK-ID>/<handle>/`.

---

## 4) Missions P0 (priorité immédiate — stabilité & never-empty)

### FC-P0-001 — News: UI empty-safe (frontend)

**Objectif**: `/news` ne crashe jamais.
**Plan**:

1. Dans le composant `NewsFeed`, remplacez l’accès direct par:
   `const articles = data?.articles ?? [];`
2. Rendre une empty-view si `articles.length === 0` avec un message court + date `freshness` si disponible.
3. Ajoutez un test manuel: rechargez la page quand `/api/news/feed` est temporairement vide (durant ingestion), la page doit rester stable.
   **DoD**:

* Impossible de reproduire `Cannot read properties of undefined (reading 'length')`.
* Capture écran + `curl /api/news/feed` en preuve.

---

### FC-P0-002 — Forecasts: UI empty-safe (frontend)

**Objectif**: `/forecasts` ne crashe pas si aucune ligne.
**Plan**:

1. Dans `Forecasts.tsx`, sécurisez la liste:
   `const rows = data?.rows ?? [];`
2. Empty-view: “Aucune prévision disponible. Le modèle est en cours de calcul.”
3. Affichez la `freshness` si disponible.
   **DoD**:

* Fin des erreurs `reading 'map'`.
* Capture + `curl /api/forecasts` jointes.

---

### FC-P0-003 — Contrats API publiés (backend/docs)

**Objectif**: un doc unique `backend/api/contracts.md` décrivant les sorties **réelles**.
**Plan**:

* Documentez les clés **obligatoires** par endpoint:

  * `/api/news/feed`: `{ articles: Array<NewsArticle>, freshness, source[] }`
  * `/api/forecasts`: `{ rows: Array<ForecastRow>, freshness, source[] }`
  * `/api/brief/daily`: `{ summary, signals[], risks[], freshness }`
  * `/api/brief/weekly`: `{ weekly: {...}, freshness }`
  * `/api/backtests`: `{ results: [...], since, until, freshness }`
* Précisez: **jamais** `null` pour les collections, toujours `[]`.
  **DoD**:
* Doc commitée + l’UI s’aligne sur ces contrats.

---

### FC-P0-004 — Cache persistant générique (backend)

**Objectif**: `load_or_compute` + `{save,load}_json` et usage par `/news` et `/forecasts`.
**Plan**:

1. Créez `backend/storage/` avec `save_json`, `load_json` (incluez `last_update` et `source[]`).
2. Créez `backend/services/cache_layer.py` contenant `load_or_compute(key, compute_fn)`.
3. Dans les routes `news` et `forecasts`, utilisez ce cache:

   * `load_or_compute("news_feed", compute_news_feed)`
   * `load_or_compute("forecasts", compute_forecasts)`
     **DoD**:

* `curl` montre des données + `last_update`.
* Redémarrer le back sert immédiatement la dernière version (never-empty).

---

### FC-P0-005 — Weekly brief: pré-calcul instantané (backend/scheduler)

**Objectif**: `/api/brief/weekly` répond en **<200ms**.
**Plan**:

1. Job hebdo qui écrit `brief_weekly.json` (real compute).
2. L’endpoint lit **uniquement** ce fichier.
3. Ajoutez un log de durée et la date de dernière génération.
   **DoD**:

* Temps de réponse mesuré <200ms.
* Preuve par `time curl` et log du job.

---

### FC-P0-006 — Backtests: cache-first + invalidation (backend)

**Objectif**: `/api/backtests` renvoie toujours une réponse utilisée par l’UI en instantané.
**Plan**:

1. L’endpoint regarde un `backtests.json`.
2. Recalculez quand `forecasts.json` a changé (timestamp > last backtest).
3. Ajoutez quelques métriques simples (hit-rate, avg ER).
   **DoD**:

* `curl /api/backtests` renvoie un objet non-vide.
* Preuve d’invalidation correcte après nouvelle génération de `forecasts`.

---

### FC-P0-007 — ErrorBoundary global (frontend)

**Objectif**: remplacer la page d’erreur brute par un composant d’erreur propre.
**Plan**:

1. Ajoutez un ErrorBoundary haut niveau (RouterProvider `errorElement` ou wrapper global).
2. Message clair, lien “Rafraîchir”, “Ouvrir /docs” et timestamp.
   **DoD**:

* En simulant une 500, l’UI reste propre et actionable.

---

### FC-P0-008 — Freshness partout (backend+frontend)

**Objectif**: toutes les réponses incluent `freshness` et l’UI l’affiche.
**Plan**:

1. Backend: `save_json` écrit systématiquement `last_update` + `source[]`.
2. Front: chaque page affiche un badge “Mise à jour: <date> | statut: fresh/stale”.
   **DoD**:

* 3 pages au moins affichent la fraîcheur (captures).

---

### FC-P0-009 — Vite proxy + .env vérifiés (frontend/devx)

**Objectif**: garantir que le front route correctement vers `8050`.
**Plan**:

1. `.env`: `VITE_API_BASE_URL=http://localhost:8050`
2. `vite.config.ts`: proxy `'/api'` vers `http://localhost:8050`
3. Vérifiez `curl http://localhost:5173/api/health` → OK.
   **DoD**:

* Capture du `curl` côté 5173.

---

### FC-P0-010 — Pre-push local: smoke hook (infra)

**Objectif**: éviter les pushs qui cassent l’app.
**Plan**:

1. Ajoutez un hook git `pre-push` qui exécute `scripts/smoke.sh` et bloque si KO.
2. Documentez comment activer/désactiver localement (pas imposé mondialement si gênant).
   **DoD**:

* Démo d’un push bloqué quand `health` ne répond pas.

---

## 5) Missions P1 (data/ML/LLM — réalimentation)

### FC-P1-011 — News Ingest v1 (RSS multi-sources)

**Objectif**: `/api/news/feed` > 20 articles réels, mis à jour < 15 min.
**Plan**:

1. Sélectionnez 3–5 flux RSS fiables finance (tickers US).
2. Ingestion → déduplication → enrichissement (ticker mapping).
3. `save_json` → `news_feed.json` avec `articles` + `source[]` + `last_update`.
4. Scheduler: job toutes les 15 min.
   **DoD**:

* `curl` montre des articles réels, récents.
* UI news stable, aucun crash.

---

### FC-P1-012 — Feature set marché (indicateurs)

**Objectif**: features techniques prêtes pour modèle.
**Plan**:

1. `features.py`: returns, volatilité, SMA/EMA, RSI, MACD, ATR; merge macro regime.
2. Sauvegardez features par ticker/interval (parquet ou json).
   **DoD**:

* Fichier features créé; exemple de 2 tickers traités; logs de durée.

---

### FC-P1-013 — Forecasts Hybrid v1 (ML + G4F ranking) - CLAIMED

**Objectif**: produire des prévisions réelles, expliquer et stocker.
**Plan**:

1. ML: prédire direction + probabilité (LightGBM/Prophet au choix).
2. LLM (G4F): re-ranker/filtrer, générer une courte explication.
3. Agrégez en `{rows: [...]}` et `save_json("forecasts.json")`.
4. L’endpoint lit le snapshot (instantané).
   **DoD**:

* `/api/forecasts` non vide, UI affiche des lignes + explication courte.

**Claimed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

---

### FC-P1-014 — Alerts (signals + news)

**Objectif**: des alertes combinant signaux techniques, news, et forecasts.
**Plan**:

1. Définissez 3 règles simples (ex: RSI<30 + news négatives + forecast down).
2. Générez une liste triée par confiance, sauvegardez `alerts.json`.
3. Servez via `/api/alerts`.
   **DoD**:

* `/api/alerts` renvoie des objets utiles, UI exploitable.

---

### FC-P1-015 — Backtests v1

**Objectif**: valider les forecasts avec des métriques simples.
**Plan**:

1. Simulez sur une période courte (ex: 30 derniers jours).
2. Calcul: hit-rate, avg expected vs realized.
3. `backtests.json` persisté + endpoint instantané.
   **DoD**:

* Résultats lisibles et stables, preuve `curl`.

---

## 6) Bons réflexes (pour livrer propre)

* **Cherchez avant de coder**: regardez s’il existe déjà une fonction proche, un dossier, une route.
* **Annoncez le plan** (2–3 lignes) dans l’issue interne ou `TASKS_BOARD.md` avant d’écrire le code.
* **Petites unités**: livrez par tronçons cohérents et testables.
* **Un agent = une mission**: concentrez-vous; pas de multi-tâches.
* **Preuve ou ça n’existe pas**: capture/log/curl/UI obligatoire dans `proofs/`.

---

## 7) Templates utiles

### Commit message

```
done:  FC-P0-006 – backtests cache-first + invalidation sur forecasts (+120) par ALEX-BACKEND-SUPERMAN-7.md Yoohoo!!! hahaa
```

### Check-in quotidien (optionnel dans `CHECKINS.md`)

```
[UTC 2025-11-03]
Hier: terminé FC-P0-004 (cache). 
Aujourd’hui: FC-P0-006 (backtests cache).
Blocages: aucun.
```

---

## 8) Anti-patterns (à éviter absolument)

* Coder sans lock → collision assurée.
* Push sans smoke test → casse l’app pour les autres.
* Masquer une erreur UI au lieu de la corriger à la source.
* Réponses API vides ou `null` pour des listes.
* “Ça marche sur ma machine” sans preuve.

---

### Dernier mot

Vous avez tout ce qu’il faut pour livrer **vite, propre, réel**.
Claim une tâche P0, suivez le plan d’intégration, **montrez vos preuves**, poussez.
On avance ensemble, sans casser, et sans faire double travail.
Let’s ship. 🚀

# ✅ Bonnes pratiques 


## 1) Prendre une tâche (anti-collision)

* Crée un **lock** avant tout: `.locks/<TASK-ID>.lock`
* Un lock = la tâche est à toi (supprime-le dans le même commit quand terminé)
* Un agent = **une tâche à la fois**
* Mets la tâche en **CLAIMED** dans le board avec ton @handle

## 2) Démarrer/arrêter l’app (standard obligatoire)

* Toujours via:

  ```bash
  /Users/venom/Documents/analyse-financiere/finance-copilot.sh start
  /Users/venom/Documents/analyse-financiere/finance-copilot.sh stop
  /Users/venom/Documents/analyse-financiere/finance-copilot.sh status
  ```
* **Ne** pas lancer `uvicorn`, `npm run dev`, `docker` directement
* Ports réservés: **Frontend 5173** / **Backend 8050**

## 3) “Never empty” data (contrats API)

* Les collections = **toujours** `[]`, jamais `null`
* Inclure **toujours**: `last_update` (UTC ISO-8601), `source[]`, `version`
* Servez **snapshot** + rafraîchissement en arrière-plan
* Utiliser un helper cache:

  ```python
  data = load_or_compute("key", compute_fn)
  ```

## 4) UI incassable (guards)

* Toujours garder:
  `const rows = data?.rows ?? []`
* Afficher un **empty-state** propre si vide
* Un crash UI = bug bloquant

## 5) Caching & persistance

* Pré-calculer ce qui est lent (weekly brief, backtests)
* Sauvegarder sur disque **après** compute (json/parquet)
* Invalider le cache **à l’événement** (ex: nouveaux forecasts → backtests)

## 6) Observabilité minimale

* Logguer: durée de compute, source(s), statut du cache, timestamp
* Ajouter un **smoke test** local et l’exécuter avant push:

  ```bash
  curl -sS http://localhost:8050/api/health | grep -i ok
  curl -sS http://localhost:8050/api/news/feed | grep -i articles
  curl -sS http://localhost:8050/api/forecasts | grep -i rows
  curl -sS http://localhost:8050/api/brief/weekly | head -c 200
  curl -sS http://localhost:8050/api/backtests | head -c 200
  ```

## 7) Commits (simples, atomiques, traçables)

* Pas de PR pour le moment
* Un commit = **uniquement** les fichiers que tu as modifiés
* Inclure **preuve** dans `proofs/<TASK-ID>/<handle>/` (capture/log/curl)
* Message:

  ```
  claim: <TASK-ID> by @handle
  done: <TASK-ID> – <résumé bref> (+<points>)
  ```

## 8) Bon workflow avant de coder

* Lire code existant (réutiliser > étendre > créer)
* Chercher dans le repo (VSCode search, ripgrep)
* Vérifier qu’aucun autre lock n’existe
* Écrire un mini-plan (3–5 étapes) dans le board avant d’implémenter

## 9) Définition de Fini (DoD) — checklist

* Endpoint répond **instantané** (snapshot) et **jamais vide**
* Données réelles, pas de mock
* UI protégée (aucun crash possible)
* `freshness` et `source[]` présents
* Smoke test **passé** + **preuve** jointe
* Lock supprimé + tâche passée en **DONE**

## 10) Performance & DX

* Endpoints “cached” < **200 ms**
* Éviter N+1 requêtes (regrouper côté backend)
* Mesurer avant/après si vous optimisez

## 11) Sécurité & secrets

* **Jamais** commiter de secrets/API keys
* Utiliser `.env.local` ignoré par git
* Nettoyer logs si sensibles

## 12) Schéma de données (raccourci)

* **Dates**: UTC, ISO-8601
* **Collections**: `[]`, jamais `null`
* **Clés minimales**:

  * `last_update`, `source[]`, `version`
* **Erreurs**: retourner `error: {code, message}`, pas de HTML

## 13) Frontend dev (rappels)

* `.env`: `VITE_API_BASE_URL=http://localhost:8050`
* `vite.config.ts`: proxy `/api` → `http://localhost:8050`
* Ajouter un **ErrorBoundary** global
* Afficher une **freshness badge** dans chaque page

## 14) Backend dev (rappels)

* Dossiers conseillés:

  * `backend/storage/` (save/load json/parquet)
  * `backend/services/cache_layer.py` (load_or_compute)
  * `backend/jobs/` (news, forecasts, weekly_brief, backtests)
  * `backend/scheduler/` (APScheduler)
* Routes = lecture snapshot + trigger async si besoin

## 15) Avant de pousser (mini check)

* `status` OK
* Smoke test OK
* Preuves ajoutées
* Lock supprimé
* Task passée à **DONE**

## 16) Anti-patterns (interdits)

* Mock data
* Collections `null`
* Lancer serveurs sans script
* Changer de ports
* “Ça marche chez moi” sans preuve

## 17) Culture projet

* On **dit** la vérité du système (pas de camouflage)
* On **répare** à la source (pas de pansement UI)
* On **documente** ce qui compte (court + utile)
* On **livre** petit mais sûr, avec **preuves**

