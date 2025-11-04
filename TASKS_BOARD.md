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




###################################################### TASKS LIST Yeeey!!!####################################################################


# 🔥 P0 — Stabilité & “Never-Empty”

## FC-P0-001 — News: UI empty-safe (frontend)

**But**: `/news` ne crashe jamais, même si l’API renvoie un snapshot vide.

**Fichiers**

* `webapp/src/components/news/NewsFeed.tsx`
* (optionnel) `webapp/src/components/ui/EmptyState.tsx`
* `webapp/src/api/client.ts` (pour le typage de retour)

**Étapes**

1. **Guard systématique**
   Remplacez tout accès direct par un fallback sûr :

   ```ts
   // NewsFeed.tsx
   const { data, isLoading, error } = useNewsFeed();
   const articles = data?.articles ?? [];         // <= garde
   const freshness = data?.freshness ?? null;
   ```
2. **Empty-view propre**
   Si `articles.length === 0`, rendre un composant d’état vide court :

   ```tsx
   if (isLoading) return <div>Chargement…</div>;
   if (error)     return <div>Impossible de charger le flux pour le moment.</div>;
   if (!articles.length) {
     return (
       <EmptyState
         title="Aucun article disponible"
         hint={freshness ? `Dernière mise à jour: ${new Date(freshness).toLocaleString()}` : "Ingestion en cours…"}
       />
     );
   }
   ```
3. **Rendu liste sécurisé**

   ```tsx
   return (
     <ul className="space-y-3">
       {articles.map(a => (
         <li key={a.id ?? a.link}>
           <NewsCard article={a} />
         </li>
       ))}
     </ul>
   );
   ```
4. **Typage côté client** (évite `undefined`)

   ```ts
   // api types – ne jamais retourner null pour des listes
   export type NewsFeedResponse = {
     articles: Array<NewsArticle>;  // [] si vide
     freshness?: string;            // ISO-8601
     source?: string[];
     version?: string;
   };
   ```
5. **Test manuel**

   * Coupez temporairement la data (`mv news_feed.json news_feed.json.bak`) pour forcer un snapshot vide.
   * Rechargez `/news`: aucune erreur, empty-state visible.
   * Restaurez le fichier.

**DoD**

* Impossible de reproduire `Cannot read properties of undefined (reading 'length')`.
* **Preuves à joindre** : capture de `/news` vide + sortie `curl -sS :8050/api/news/feed | jq .`.

---

## FC-P0-002 — Forecasts: UI empty-safe (frontend)

**But**: `/forecasts` affiche un état vide propre et ne crashe pas.

**Fichiers**

* `webapp/src/pages/Forecasts.tsx`
* (optionnel) `webapp/src/components/ui/EmptyState.tsx`

**Étapes**

1. **Guard sur rows**

   ```ts
   const { data, isLoading, error } = useForecasts();
   const rows = data?.rows ?? [];
   const freshness = data?.freshness ?? null;
   ```
2. **Empty-view**

   ```tsx
   if (!rows.length) {
     return (
       <EmptyState
         title="Aucune prévision disponible"
         hint={freshness ? `Dernière mise à jour: ${new Date(freshness).toLocaleString()}` : "Le modèle calcule en arrière-plan…"}
       />
     );
   }
   ```
3. **Rendu table sécurisé**

   ```tsx
   <tbody>
     {rows.map(r => (
       <tr key={r.id ?? `${r.symbol}-${r.horizon}`}>
         <td>{r.type}</td><td>{r.symbol}</td><td>{r.horizon}</td>
         <td>{r.score?.toFixed?.(2) ?? "-"}</td>
         <td>{r.dir ?? "-"}</td><td>{Math.round((r.confidence ?? 0)*100)}%</td>
       </tr>
     ))}
   </tbody>
   ```

**DoD**

* Plus d’erreurs `reading 'map'`.
* **Preuves** : capture `/forecasts` vide + `curl -sS :8050/api/forecasts | jq .`.

---

## FC-P0-003 — Contrats API publiés (backend/docs) - DONE

**But**: un **contrat unique, source de vérité** pour le front.

**Fichiers**

* `backend/api/contracts.md` (nouveau)
* (bonus) `backend/api/schemas/*.json` pour JSON Schema

**Contenu minimal à documenter**

* **/api/news/feed**

  ```json
  {
    "articles": [ { "id": "string", "title": "string", "link": "url", "pubDate": "ISO-8601", "tickers": ["AAPL"], "sentiment_score": 0.12 } ],
    "freshness": "ISO-8601",
    "source": ["rss:reuters","rss:bloomberg"],
    "version": "v1"
  }
  ```
* **/api/forecasts**

  ```json
  {
    "rows": [ { "type": "stock", "symbol": "AAPL", "horizon": "1d", "score": 0.41, "dir": "up|down", "confidence": 0.67, "explanation": "string" } ],
    "freshness": "ISO-8601",
    "source": ["ml","llm"],
    "version": "v1"
  }
  ```
* **Règles globales**: collections **jamais** `null`, toujours `[]`; dates **ISO-8601 UTC**; `version` optionnelle; `error:{code,message}` en cas d’erreur.

**DoD**

* Fichier committé, simple à lire, et le front s’aligne (aucun accès à des champs non documentés).

**Completed by**: ALEX-API-ARCHITECT-SUPERMAN-7

---

## FC-P0-004 — Cache persistant générique (backend)

**But**: un helper **`load_or_compute`** fiable pour servir un snapshot **instantané**.

**Fichiers**

* `backend/storage/io.py` — `save_json`, `load_json`
* `backend/services/cache_layer.py` — `load_or_compute`
* `backend/routes/news.py`, `backend/routes/forecasts.py` — utilisation

**Étapes**

1. **I/O JSON**

   ```py
   # backend/storage/io.py
   from pathlib import Path
   import json, time, datetime as dt

   BASE = Path("data")  # gitignored

   def save_json(key: str, payload: dict, source: list[str] = None, version: str = "v1"):
       BASE.mkdir(parents=True, exist_ok=True)
       payload = dict(payload)
       payload["freshness"] = dt.datetime.utcnow().isoformat()+"Z"
       payload["source"] = source or []
       payload["version"] = version
       (BASE / f"{key}.json").write_text(json.dumps(payload, ensure_ascii=False))

   def load_json(key: str) -> dict | None:
       p = BASE / f"{key}.json"
       return json.loads(p.read_text()) if p.exists() else None
   ```
2. **Cache layer**

   ```py
   # backend/services/cache_layer.py
   from typing import Callable
   from backend.storage.io import load_json, save_json

   def load_or_compute(key: str, compute_fn: Callable[[], dict]):
       snapshot = load_json(key)
       if snapshot: 
           return snapshot  # never-empty
       data = compute_fn()           # <- vrai calcul
       save_json(key, data, source=["compute:"+key])
       return load_json(key)
   ```
3. **Utilisation route**

   ```py
   # backend/routes/news.py
   from fastapi import APIRouter
   from backend.services.cache_layer import load_or_compute
   from backend.jobs.news_ingest import compute_news_feed

   router = APIRouter()

   @router.get("/api/news/feed")
   def news_feed():
       return load_or_compute("news_feed", compute_news_feed)
   ```

**DoD**

* `curl :8050/api/news/feed` renvoie un objet avec `freshness`.
* Redémarrage backend → toujours une réponse (snapshot).

---

## FC-P0-005 — Weekly brief pré-calculé (backend/scheduler)

**But**: `/api/brief/weekly` < 200ms.

**Fichiers**

* `backend/jobs/weekly_brief.py` — `compute_weekly_brief()`
* `backend/scheduler/app.py` — APScheduler
* `backend/routes/brief.py`

**Étapes**

1. **Job compute**

   ```py
   # backend/jobs/weekly_brief.py
   from backend.storage.io import save_json

   def compute_weekly_brief() -> dict:
       # … calcul réel: top signaux/risques, résumé, stats …
       return {"weekly": {"summary":"...", "signals":[], "risks":[]}}

   def run_and_persist():
       payload = compute_weekly_brief()
       save_json("brief_weekly", payload, source=["job:weekly_brief"])
   ```
2. **Scheduler**

   ```py
   # backend/scheduler/app.py
   from apscheduler.schedulers.background import BackgroundScheduler
   from backend.jobs.weekly_brief import run_and_persist

   sched = BackgroundScheduler()
   sched.add_job(run_and_persist, "cron", day_of_week="sun", hour=23, minute=30)
   sched.start()
   ```
3. **Route lecture-snapshot**

   ```py
   # backend/routes/brief.py
   from fastapi import APIRouter
   from backend.storage.io import load_json

   router = APIRouter()

   @router.get("/api/brief/weekly")
   def weekly():
       return load_json("brief_weekly") or {"weekly": {}, "freshness": None}
   ```

**DoD**

* `time curl :8050/api/brief/weekly` < 200ms (preuve + capture logs de job).

---

## FC-P0-006 — Backtests: cache-first + invalidation (backend)

**But**: `/api/backtests` instantané et auto-recalcule si `forecasts` a changé.

**Fichiers**

* `backend/jobs/backtests.py`
* `backend/routes/backtests.py`

**Étapes**

1. **Métadonnées de dépendance**

   * Lisez `freshness` de `forecasts.json`.
   * Stockez dans `backtests.json` un champ `depends_on_forecasts: "<iso>"`.
2. **Invalidation**

   ```py
   from backend.storage.io import load_json, save_json

   def compute_backtests():
       # charger forecasts + marché et simuler
       return {"results":[...], "since":"...", "until":"..."}

   def ensure_backtests_up_to_date():
       bt = load_json("backtests")
       fc = load_json("forecasts")
       fc_ts = fc.get("freshness") if fc else None
       need = not bt or (bt.get("depends_on_forecasts") != fc_ts)
       if need:
           data = compute_backtests()
           data["depends_on_forecasts"] = fc_ts
           save_json("backtests", data, source=["job:backtests"])
       return load_json("backtests")
   ```
3. **Route**

   ```py
   @router.get("/api/backtests")
   def backtests():
       return ensure_backtests_up_to_date()
   ```

**DoD**

* `curl` renvoie des résultats non-vides.
* Après nouveau `forecasts.json`, `depends_on_forecasts` change (preuve).

---

## FC-P0-007 — ErrorBoundary global (frontend)

**But**: remplacer l’écran d’erreur brut par une UX maîtrisée.

**Fichiers**

* `webapp/src/components/system/ErrorBoundary.tsx`
* `webapp/src/main.tsx` (ou `App.tsx`) / Router

**Étapes**

1. **Composant**

   ```tsx
   import React from "react";

   export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { error?: any }> {
     state = { error: undefined };
     static getDerivedStateFromError(error: any) { return { error }; }
     render() {
       if (this.state.error) {
         return (
           <div className="p-6">
             <h2>Un problème est survenu.</h2>
             <p>Essayez de rafraîchir. Si ça persiste, ouvrez /docs.</p>
             <button onClick={() => location.reload()}>Rafraîchir</button>
             <div className="text-xs mt-2">{new Date().toLocaleString()}</div>
           </div>
         );
       }
       return this.props.children;
     }
   }
   ```
2. **Intégration**

   ```tsx
   // main.tsx
   ReactDOM.createRoot(document.getElementById('root')!).render(
     <ErrorBoundary>
       <RouterProvider router={router} />
     </ErrorBoundary>
   );
   ```

**DoD**

* Simulation d’une exception → UI propre, boutons visibles (capture).

---

## FC-P0-008 — Freshness partout (backend+frontend)

**Status**: DONE by ALEX-BACKEND-SUPERMAN-7

**But**: chaque réponse **inclut** `freshness`, l'UI **l’affiche**.

**Fichiers**

* `backend/storage/io.py` (déjà fait)
* `webapp/src/components/ui/FreshnessBadge.tsx` (nouveau)
* Pages : `/`, `/news`, `/forecasts`, `/backtests`, `/brief`

**Étapes**

1. **Badge**

   ```tsx
   export function FreshnessBadge({ freshness, stale }: { freshness?: string|null, stale?: boolean }) {
     if (!freshness) return null;
     const label = `Mise à jour: ${new Date(freshness).toLocaleString()}`;
     return <span className={`badge ${stale ? "badge-warning" : "badge-ok"}`}>{label}{stale ? " • stale" : ""}</span>;
   }
   ```
2. **Usage**

   ```tsx
   <div className="flex items-center justify-between">
     <h1>News</h1>
     <FreshnessBadge freshness={data?.freshness} stale={data?.stale}/>
   </div>
   ```

**DoD**

* Au moins 3 pages montrent le badge (captures).

---

## FC-P0-009 — Vite proxy + .env (frontend/devx)

**But**: le front parle au back via `/api` local.

**Fichiers**

* `webapp/.env.local`
* `webapp/vite.config.ts`

**Étapes**

1. **Env**

   ```
   VITE_API_BASE_URL=http://localhost:8050
   ```
2. **Proxy**

   ```ts
   // vite.config.ts
   export default defineConfig({
     server: {
       proxy: { "/api": "http://localhost:8050" }
     }
   })
   ```
3. **Test**

   * `curl -sS http://localhost:5173/api/health` → `ok`.

**DoD**

* Capture du `curl` côté 5173.

---

## FC-P0-010 — Pre-push local: smoke hook (infra)

**But**: empêcher un push qui casse l’app.

**Fichiers**

* `scripts/smoke.sh`
* `.git/hooks/pre-push` (local, non versionné) **+** `docs/dev/pre-push.md`

**Étapes**

1. **Smoke script**

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   curl -sS :8050/api/health | grep -qi ok
   curl -sS :8050/api/news/feed | jq -e '.articles' > /dev/null
   curl -sS :8050/api/forecasts | jq -e '.rows' > /dev/null
   curl -sS :8050/api/brief/weekly | head -c 80 > /dev/null
   curl -sS :8050/api/backtests | head -c 80 > /dev/null
   echo "SMOKE OK"
   ```
2. **Hook**

   ```bash
   # .git/hooks/pre-push (local)
   #!/usr/bin/env bash
   [ "${BYPASS_SMOKE:-0}" = "1" ] && exit 0
   ./scripts/smoke.sh || { echo "SMOKE KO — push bloqué"; exit 1; }
   ```
3. **Doc**: comment activer/désactiver (`chmod +x`, var BYPASS_SMOKE=1).

**DoD**

* Démo d’un push bloqué si `/api/health` KO (preuve terminal).

---

# 📈 P1 — Data / ML / LLM

## FC-P1-011 — News Ingest v1 (RSS multi-sources)

**But**: > 20 articles réels, refresh < 15 min.

**Fichiers**

* `backend/jobs/news_ingest.py`
* `backend/routes/news.py` (déjà)
* `backend/scheduler/app.py` (cron 15 min)

**Étapes**

1. **Sources**
   Préparez une liste 3–5 flux finance/économie (US large-caps).

   ```py
   SOURCES = [
     {"name":"reuters",   "url":"https://.../businessNews"},
     {"name":"bloomberg", "url":"https://.../markets"},
     {"name":"wsj",       "url":"https://.../markets"},
   ]
   ```
2. **Ingestion RSS** (avec `feedparser` ou `xml.etree`)

   ```py
   def fetch_feed(url): ...
   def normalize(entry, source):
       return {
         "id": entry.get("id") or entry.get("link"),
         "title": entry.get("title"),
         "link": entry.get("link"),
         "pubDate": iso_utc(entry.get("published_parsed")),
         "source": source["name"]
       }
   ```
3. **Dédup + enrichissement**

   * Clé = `(title|link|pubDate)` normalisés.
   * `ticker mapping` simple (regex `\b[A-Z]{1,5}\b` + dictionnaire S&P500).
4. **Snapshot**

   ```py
   payload = {"articles": articles_sorted_desc}
   save_json("news_feed", payload, source=[s["name"] for s in SOURCES])
   ```
5. **Scheduler**
   Job toutes les 15 min → `run_news_ingest()`.

**DoD**

* `jq '.articles|length'` ≥ 20.
* Articles < 15 minutes pour certains flux.

**Preuves**

* `curl` + capture `/news` stable.

---

## FC-P1-012 — Feature set marché (indicateurs)

**But**: features techniques prêtes pour le modèle.

**Fichiers**

* `backend/features/features.py`
* `data/market/<TICKER>.csv` (ou téléchargement via yfinance/ccxt selon ce que vous avez déjà)

**Étapes**

1. **Chargement prix** (OHLCV)
2. **Indicateurs** (sans dépendances lourdes) :

   ```py
   def sma(s, w): return s.rolling(w).mean()
   def rsi(close, w=14): # calc gains/pertes moyennes
       delta = close.diff()
       up, down = delta.clip(lower=0), -delta.clip(upper=0)
       rs = up.rolling(w).mean() / down.rolling(w).mean()
       return 100 - (100 / (1 + rs))
   # EMA, MACD, ATR idem
   ```
3. **Merge macro regime** (si dispo) et **export** parquet/json.

**DoD**

* Fichier features écrit pour 2 tickers (preuve `ls -lh` + extrait `jq`).

---

## FC-P1-013 — Forecasts Hybrid v1 (ML + G4F) — *CLAIMED*

**But**: produire de vraies lignes de forecast.

**Fichiers**

* `backend/models/ml_forecast.py`
* `backend/models/llm_ranker.py`
* `backend/jobs/forecasts.py`
* `backend/routes/forecasts.py`

**Étapes (guideline pour l’agent)**

1. ML binaire (up/down) + proba (LightGBM / logistic).
2. Générer `candidate_rows` = [{symbol,horizon,score,confidence_raw}].
3. LLM (G4F) : re-ranking + génération d’`explanation` courte.
4. `save_json("forecasts", {"rows": ranked})`.

**DoD**

* `/api/forecasts` non vide, champs conformes au contrat.

---

## FC-P1-014 — Alerts (signals + news)

**But**: règles simples conciliant technique + news + forecast.

**Fichiers**

* `backend/jobs/alerts.py`
* `backend/routes/alerts.py`

**Étapes**

1. **Règles** (exemples)

   * **Oversold-Bearish**: `RSI<30` AND news sentiment < −0.3 AND forecast dir=`down`.
   * **Overbought-Bullish**: `RSI>70` AND sentiment > 0.3 AND forecast dir=`up`.
   * **Breakout News**: volatilité ↑ ET ≥2 articles taggés `TICKER` dans 1h.
2. **Score confiance**: moyenne pondérée (forecast.confidence, |sentiment|, force signal).
3. **Snapshot**:

   ```py
   save_json("alerts", {"alerts": sorted_alerts})
   ```

**DoD**

* `/api/alerts` liste triée, exploitable côté UI.

---

## FC-P1-015 — Backtests v1

**But**: hit-rate minimal + ER moyen.

**Fichiers**

* `backend/jobs/backtests.py` (même module que P0-006 acceptable)

**Étapes**

1. **Jeu de règles simple**

   * Prendre positions 1d suivant la direction prédite, seuil min `confidence>=0.55`.
2. **Calcul**

   * `hit_rate = correct / total`
   * `avg_er = mean( sign(pred_dir) * (close_t+1 - close_t) / close_t )`
3. **Sauvegarde** → `backtests.json`.

**DoD**

* Résultats lisibles (`hit_rate`, `avg_er`, `n_trades`), preuve `curl`.

---
############################################ END OF TASKS LIST Yeeey!!!####################################################################

























---

### Rappels 

* **Claim**: `git commit -m "claim: <TASK-ID> by @handle"`
* **Done**: `git commit -m "done: <TASK-ID> – <résumé bref> (+<points>)" AGENT NAME yeees!! yoohooo! Goal!`
* **Preuves**: `proofs/<TASK-ID>/<handle>/` (captures, `curl`, logs)
* **Toujours** supprimer le lock dans le commit “done”.

Bonne chasse, agents. Choisissez une tâche, **lockez**, livrez **propre**, **preuve à l’appui**. On garde le cap: **zéro mock**, **never-empty**, **instantané**. 🚀

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

