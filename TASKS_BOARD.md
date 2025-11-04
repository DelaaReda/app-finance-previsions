# 📣 MESSAGE AUX AGENTS — Lisez-moi et démarrez

Équipe, bienvenue dans **Finance Copilot**.
Ici on livre **du vrai**: zéro mock, zéro “quick fix” qui masque les problèmes.
Votre mission: **rendre l’app stable, rapide et alimentée par de la vraie data**.

---

## ⚠️ HOTFIX CRITIQUE — backend ne démarre pas (immédiat)

### Problème identifié par le DATA QUALITY MANAGER
Le backend **ne peut pas démarrer** en raison d'erreurs critiques d'imports :
- `ModuleNotFoundError: No module named 'core'` 
- `from core.middleware import FinanceMiddleware` → fichier inexistant
- `from core.data_access import ...` → fichier inexistant
- `from src.api.services.news_service import news_service` → fichier inexistant
- `from src.api.services.forecast_service import forecast_service` → fichier inexistant

### Plan d'action immédiat
Les tâches suivantes sont prioritaires pour réparer le backend :

#### FC-HOTFIX-001 — Structurer le backend en vrai package
**Status**: DONE by ALEX-BACKEND-SUPERMAN-7

**But**: supprimer `ModuleNotFoundError` et fiabiliser les imports.
**À faire**
1. Créer les dossiers + `__init__.py` :
```
backend/
  api/__init__.py
  api/main.py
  api/routes/__init__.py
  api/routes/health.py
  api/routes/news.py
  api/routes/forecasts.py
  core/__init__.py
  core/middleware.py
  core/response.py
  services/__init__.py
  services/cache_layer.py
  services/news_service.py
  services/forecast_service.py
  storage/__init__.py
  storage/io.py
```

2. S'assurer que **tous** les imports utilisent ces chemins **absolus** (p.ex. `from core.middleware import FinanceMiddleware`, `from services.news_service import get_news_feed`).
3. Ajouter un **`PYTHONPATH=.`** dans le script de démarrage.
**DoD**
* `uvicorn api.main:app --port 8050` démarre sans erreur.
* `curl :8050/api/health` renvoie `{ ok:true }`.

#### FC-HOTFIX-002 — Middlewares & envelope de réponse
**Status**: CLAIMED

**But**: avoir un middleware minimal et une réponse standard `{ ok, data }`.

**Claimed by**: ALEX-API-ARCHITECT-SUPERMAN-7

#### FC-HOTFIX-003 — `main.py` propre + routes incluses
**Status**: AVAILABLE to claim

**But**: app FastAPI minimaliste mais clean.

#### FC-HOTFIX-004 — I/O disque + cache léger (never-empty)
**Status**: AVAILABLE to claim

**But**: lecture/écriture JSON + métadonnées de fraîcheur.

#### FC-HOTFIX-005 — Services & routes "news" et "forecasts"
**Status**: AVAILABLE to claim

**But**: endpoints **réels** + snapshot.

#### FC-HOTFIX-006 — Script start/stop/status sans `timeout`
**Status**: AVAILABLE to claim

**But**: démarrage stable sur macOS (pas de `timeout`).

#### FC-HOTFIX-007 — Front: enveloppe + empty-states
**Status**: AVAILABLE to claim

**But**: plus de crash `length/map of undefined`.

#### FC-HOTFIX-008 — Smoke sans `timeout`
**Status**: AVAILABLE to claim

**But**: pre-push fiable sur macOS.

**REMARQUE IMPORTANTE**: Tant que ces HOTFIX ne sont pas résolus, l'application est non fonctionnelle. 
Priorité absolue à la réparation du backend avant toute autre fonctionnalité.

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




Tu as raison : là, le backend **ne peut pas démarrer** (imports cassés, `timeout` absent, mauvais chemins). On corrige **tout de suite** avec un plan “hotfix” ultra-précis que tu peux coller au board pour les agents. J’ai mis le **pourquoi**, le **comment** et des **snippets prêts à coller**.

---

# 🔧 HOTFIX — remettre le backend sur pied (immédiat)

## Pourquoi ça plante

* `ModuleNotFoundError: No module named 'core'` → l’arborescence Python n’est pas un **package** (pas de `__init__.py`) et les **imports** ne correspondent pas aux dossiers réels.
* Le script d’agent a tenté d’utiliser `timeout` (absent sur macOS) → commandes KO.
* Le front tape probablement aux **mauvaises URLs** (`/forecasts` vs `/api/forecasts`) et **l’enveloppe** `{ ok, data }` n’est pas gérée côté UI.

---

## 🎯 Objectif hotfix

1. Rendre le backend **bootable** (`uvicorn api.main:app` OK).
2. Fixer la structure de **packages** + **imports**.
3. Exposer 3 routes **fonctionnelles**: `/api/health`, `/api/news/feed`, `/api/forecasts` (never-empty avec snapshot disque).
4. Éviter `timeout` ; remplacer par un **wait loop** simple.
5. Côté front, consommer **l’enveloppe** `{ ok, data }` et sécuriser les empty-states.

---

## ✅ À coller dans `TASKS_BOARD.md` — tâches prêtes à claimer

### FC-HOTFIX-001 — Structurer le backend en vrai package

**Status**: DONE by ALEX-BACKEND-SUPERMAN-7

**But**: supprimer `ModuleNotFoundError` et fiabiliser les imports.
**À faire**

1. Créer les dossiers + `__init__.py` :

```
backend/
  api/__init__.py
  api/main.py
  api/routes/__init__.py
  api/routes/health.py
  api/routes/news.py
  api/routes/forecasts.py
  core/__init__.py
  core/middleware.py
  core/response.py
  services/__init__.py
  services/cache_layer.py
  services/news_service.py
  services/forecast_service.py
  storage/__init__.py
  storage/io.py
```

2. S’assurer que **tous** les imports utilisent ces chemins **absolus** (p.ex. `from core.middleware import FinanceMiddleware`, `from services.news_service import get_news_feed`).
3. Ajouter un **`PYTHONPATH=.`** dans le script de démarrage (voir FC-HOTFIX-003).
   **DoD**

* `uvicorn api.main:app --port 8050` démarre sans erreur.
* `curl :8050/api/health` renvoie `{ ok:true }`.

---

### FC-HOTFIX-002 — Middlewares & envelope de réponse

**But**: avoir un middleware minimal et une réponse standard `{ ok, data }`.
**Fichiers (à créer)**

`backend/core/response.py`

```python
from fastapi.responses import JSONResponse

def ok(data):
    return {"ok": True, "data": data}

def err(code:int, message:str):
    return JSONResponse({"ok": False, "error": {"code": code, "message": message}}, status_code=code)
```

`backend/core/middleware.py`

```python
import time
from starlette.middleware.base import BaseHTTPMiddleware

class FinanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        response.headers["X-Exec-Time-ms"] = str(int((time.time()-start)*1000))
        return response
```

**DoD**

* Les routes utilisent `from core.response import ok, err`.
* Health renvoie `ok({...})`.

---

### FC-HOTFIX-003 — `main.py` propre + routes incluses

**But**: app FastAPI minimaliste mais clean.
**Remplacer** `backend/api/main.py` par :

```python
from fastapi import FastAPI
from core.middleware import FinanceMiddleware
from api.routes.health import router as health_router
from api.routes.news import router as news_router
from api.routes.forecasts import router as forecasts_router

app = FastAPI(title="Finance Copilot API")
app.add_middleware(FinanceMiddleware)
app.include_router(health_router, prefix="/api")
app.include_router(news_router, prefix="/api")
app.include_router(forecasts_router, prefix="/api")
```

`backend/api/routes/health.py`

```python
from fastapi import APIRouter
from core.response import ok
from storage.io import last_updates_info

router = APIRouter()

@router.get("/health")
def health():
    return ok({"status": "ok", "last_updates": last_updates_info()})
```

**DoD**

* `uvicorn api.main:app --port 8050` up → `curl :8050/api/health` OK.

---

### FC-HOTFIX-004 — I/O disque + cache léger (never-empty)

**But**: lecture/écriture JSON + métadonnées de fraîcheur.
**Créer** `backend/storage/io.py`

```python
from pathlib import Path
import json, time

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)

def _path(key:str) -> Path:
    return DATA_DIR / f"{key}.json"

def save_json(key:str, payload:dict, source:list|None=None):
    now = int(time.time())
    doc = {
        "last_update": now,
        "source": source or [],
        "version": 1,
        "payload": payload
    }
    _path(key).write_text(json.dumps(doc, ensure_ascii=False))
    return doc

def load_json(key:str) -> dict|None:
    p = _path(key)
    if not p.exists(): return None
    return json.loads(p.read_text())

def last_updates_info():
    info = {}
    for name in ["news_feed","forecasts","brief_weekly","backtests"]:
        d = load_json(name)
        if d: info[name] = d.get("last_update")
    return info
```

**Créer** `backend/services/cache_layer.py`

```python
from storage.io import load_json, save_json

def load_or_compute(key:str, compute_fn, source:list|None=None):
    snap = load_json(key)
    if snap and snap.get("payload") is not None:
        return snap
    data = compute_fn()
    return save_json(key, data, source=source)
```

**DoD**

* `save_json/load_json` opérationnels.
* `load_or_compute` utilisé par news/forecasts.

---

### FC-HOTFIX-005 — Services & routes “news” et “forecasts”

**But**: endpoints **réels** + snapshot.
**Créer** `backend/services/news_service.py`

```python
def compute_news_feed():
    # TODO: remplacer par l’ingest réelle RSS (P1)
    return {"articles": []}

def get_news_feed(cache):
    return cache("news_feed", compute_news_feed, source=["bootstrap"])
```

**Créer** `backend/services/forecast_service.py`

```python
def compute_forecasts():
    # TODO: remplacer par ML + G4F (P1)
    return {"rows": []}

def get_all_forecasts(cache):
    return cache("forecasts", compute_forecasts, source=["bootstrap"])
```

**Créer** `backend/api/routes/news.py`

```python
from fastapi import APIRouter
from core.response import ok
from services.news_service import get_news_feed
from services.cache_layer import load_or_compute

router = APIRouter()

@router.get("/news/feed")
def news_feed():
    snap = get_news_feed(lambda key,fn,source=None: load_or_compute(key,fn,source))
    payload = snap["payload"]
    payload["freshness"] = snap["last_update"]
    payload["source"] = snap["source"]
    return ok(payload)
```

**Créer** `backend/api/routes/forecasts.py`

```python
from fastapi import APIRouter
from core.response import ok
from services.forecast_service import get_all_forecasts
from services.cache_layer import load_or_compute

router = APIRouter()

@router.get("/forecasts")
def forecasts():
    snap = get_all_forecasts(lambda key,fn,source=None: load_or_compute(key,fn,source))
    payload = snap["payload"]
    payload["freshness"] = snap["last_update"]
    payload["source"] = snap["source"]
    return ok(payload)
```

**DoD**

* `curl :8050/api/news/feed | jq` → `{ ok:true, data:{ articles:[], freshness:..., source:[...] } }`
* `curl :8050/api/forecasts | jq` → `{ ok:true, data:{ rows:[], ... } }`

---

### FC-HOTFIX-006 — Script start/stop/status sans `timeout`

**But**: démarrage stable sur macOS (pas de `timeout`).
**Modifier** `finance-copilot.sh` (section backend) pour :

* activer venv, `export PYTHONPATH="$(pwd)/copilot-app/backend"`
* lancer uvicorn en **arrière-plan** et écrire un PID.
* **boucle d’attente** (10 tentatives) qui teste `/api/health` avec `curl -f`.

**Snippet à intégrer**

```bash
start_backend() {
  cd "$ROOT/copilot-app/backend" || exit 1
  [ -d .venv ] || python3 -m venv .venv
  source .venv/bin/activate
  pip install -U pip && pip install -r requirements.txt
  export PYTHONPATH="$(pwd)"
  uvicorn api.main:app --host 0.0.0.0 --port 8050 --reload > api.log 2>&1 &
  echo $! > .backend.pid

  # wait loop (no 'timeout')
  for i in {1..10}; do
    sleep 1
    if curl -fsS http://localhost:8050/api/health >/dev/null; then
      echo "Backend up"
      return 0
    fi
  done
  echo "Backend failed to start"; exit 1
}
```

**DoD**

* `./finance-copilot.sh start` → “Backend up”.
* `./finance-copilot.sh status` montre le PID.

---

### FC-HOTFIX-007 — Front: enveloppe + empty-states

**But**: plus de crash `length/map of undefined`.
**À faire (exemples)**

* `NewsFeed.tsx` :

```ts
const resp = useQuery(...);
const articles = resp.data?.data?.articles ?? [];
// afficher EmptyState si articles.length===0
```

* `Forecasts.tsx` :

```ts
const resp = useQuery(...);
const rows = resp.data?.data?.rows ?? [];
```

* Vérifier que **toutes** les pages lisent `resp.data?.data?.…`.
  **DoD**
* `/news` et `/forecasts` ne crashent **jamais** (captures).
* Empty-view + badge “Mise à jour: …”.

---

### FC-HOTFIX-008 — Smoke sans `timeout`

**But**: pre-push fiable sur macOS.
**Créer** `scripts/smoke.sh`

```bash
set -euo pipefail
curl -fsS http://localhost:8050/api/health | grep -q '"ok": true'
curl -fsS http://localhost:8050/api/news/feed | grep -q '"articles"'
curl -fsS http://localhost:8050/api/forecasts | grep -q '"rows"'
echo "SMOKE OK"
```

**DoD**

* Hook pre-push l’exécute ; push bloqué si un check échoue.

---

## 🧭 Commentaire management (ce qu’ils doivent améliorer)

* **Toujours booter localement** avant commit. Les imports cassés = “push interdit”.
* **Interdiction d’utiliser `timeout`** (non dispo par défaut sur macOS). Préférer un **wait loop**.
* **Unifier l’enveloppe `{ ok, data }`** côté front **et** back (zéro exception).
* **Never-empty** effectif: routes lisent **uniquement** des snapshots persistés, et **calculent en arrière-plan**.
* **Preuves**: joindre le `curl /api/… | jq` + capture UI à chaque “done”.
















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

## FC-P0-014 — Health+ enrichi (backend)

**Status**: DONE by ALEX-BACKEND-SUPERMAN-7

**But**: étendre `/api/health` pour exposer `last_updates` par domaine et chemin des données.
**Fichiers**

* `backend/api/routes/health.py`

**Étapes**

1. **Données de santé**

   ```python
   @router.get("/health")
   def health():
       return ok({
         "status": "ok",
         "backend_up": True,                # service répond
         "last_updates": {                  # dernieres mises à jour par domaine
           "news": 1234567890,
           "forecasts": 1234567890,
           "brief_weekly": 1234567890,
           "backtests": 1234567890
         },
         "data_paths": {                    # chemins vers fichiers de données
           "forecasts": "/data/forecasts.json",
           "news": "/data/news_feed.json"
         }
       })
   ```
2. **UI**: badge de statut dans le header de l'application (vert/orange/rouge selon santé).
   **DoD**

* `curl /api/health | jq` montre `last_updates` et `data_paths`.
* Badge UI visible dans le header (capture).

---

# 📈 P1 — Data / ML / LLM

## FC-P1-011 — News Ingest v1 (RSS multi-sources) - DONE

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

**Completed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**Files created**:
- `/jobs/news_ingest.py` - Complete RSS ingestion pipeline with deduplication and ticker mapping
- `/scheduler/app.py` - Scheduler with 15-min job for news refresh
- `/storage/io.py` and `/services/cache_layer.py` - Used for persistent storage (from HOTFIX)

---

## FC-P1-012 — Feature set marché (indicateurs) - DONE

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

**Completed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**Files created**:
- `/features/features.py` - Complete technical indicators suite with 20+ indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR, volatility, momentum, etc.)
- `/data/features/` - Directory for saving JSON features files for each ticker

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










Parfait. J’ai lu tes derniers commits et l’état de la branche **feature/g4f-integration**. Voici les **priorités nettes** (avec raisons ancrées dans ce qui est déjà en place), puis un **découpage en tâches prêtes à claimer**.

## Ce que j’ai constaté (audit ultra-court)

* Le backend expose désormais **`/api/forecasts`** via `forecast_service.get_all_forecasts(...)` (remplacement d’un stub). ([GitHub][1])
* La doc d’archi backend impose un **enveloppe** uniforme: `{"ok": bool, "data": {...}}` et liste les endpoints critiques (`/api/forecasts`, `/api/macro/series`, `/api/news/feed`, etc.). ([GitHub][1])
* Un commit de type “done” (ex: **FC-P0-008 – Freshness**) a bien été poussé — bonne base pour le format “claim/done”. ([GitHub][1])

👉 Implication: le **front** doit lire `data.data.rows` / `data.data.articles` (et pas `data.rows`). Sinon on retombe sur les erreurs vues (`map/length of undefined`).

---

## Priorités maintenant (ordre conseillé)

1. **Aligner contrat API ↔ Front**

   * Adapter *toutes* les requêtes front pour consommer l’enveloppe `{ ok, data }` (et non des champs à la racine).
   * C’est la source #1 des crashs sur `/news` et `/forecasts`. ([GitHub][1])

2. **Proxy Vite & base URL**

   * S’assurer que les appels partent bien vers **`/api/*`** (ton backend publie `api/...`).
   * Corrige le 404 vu côté UI quand ça tape `/forecasts` au lieu de `/api/forecasts`.

3. **Empty-safety + ErrorBoundary**

   * Gardes systématiques `const rows = resp?.data?.rows ?? []` / `const articles = resp?.data?.articles ?? []`.
   * Mettre un ErrorBoundary global pour bannir les écrans d’erreur bruts.

4. **Cache persistant + Never-Empty**

   * Implémenter `load_or_compute` + `{save,load}_json` et l’activer sur **news** et **forecasts**.
   * Sert le **dernier snapshot** immédiatement; calcule en arrière-plan.

5. **Smoke tests + pre-push**

   * Bloquer tout push si `/api/health` ou les routes clés ne répondent pas avec les clés attendues.

6. **Health+ enrichi**

   * Étendre `/api/health` pour exposer `last_updates` par domaine; badge côté UI.

---

## Tâches prêtes à claimer (avec pas-à-pas précis)

### FC-P0-009 (DEVX) — Vite proxy + `.env`

**But**: 0 mismatch d’URL entre front et back.
**À faire (concret)**

* `.env`: `VITE_API_BASE_URL=http://localhost:8050`
* `vite.config.ts`: proxy `'/api' → 'http://localhost:8050'`
* Dans ton `api/client` (fetch/axios), préfixer **toujours** par `import.meta.env.VITE_API_BASE_URL` si appel absolu, sinon utiliser `/api/...`.
* **Test**: `curl http://localhost:5173/api/health` renvoie le health du back.
  **Fini si**: capture du `curl :5173/api/health` + UI `/forecasts` ne 404 plus.

---

### FC-P0-001 (UI) — News empty-safe + contrat

**But**: `/news` ne crashe jamais.
**À faire (concret)**

* Dans `NewsFeed.tsx`:

  * Remplacer accès direct par `const articles = resp?.data?.articles ?? [];`
  * Empty-view propre si `articles.length===0` (texte + `freshness` si présent).
* Vérifier que le hook/fetch **retourne l’enveloppe** brute (ne pas “déballer” côté hook si l’UI attend l’enveloppe).
* **Test manuel**: server renvoie un snapshot vide contrôlé → la page reste stable.
  **Fini si**: plus aucune `reading 'length' of undefined`; capture + `curl /api/news/feed`.

---

### FC-P0-002 (UI) — Forecasts empty-safe + contrat

**But**: `/forecasts` sans crash si vide.
**À faire**

* Dans `Forecasts.tsx`: `const rows = resp?.data?.rows ?? [];`
* Empty-view “Aucune prévision… en cours de calcul”; afficher `freshness`.
* Vérifier la **clé d’état React-Query** (ex: `["forecasts"]`) et que le **select** (si utilisé) garde l’enveloppe ou l’adapte partout.
  **Fini si**: plus de `reading 'map'`; capture + `curl /api/forecasts`.

---

### FC-P0-007 (UI) — ErrorBoundary global

**But**: adieu l’écran d’erreur brut.
**À faire**

* Créer `components/ErrorBoundary.tsx` (render fallback + bouton “Rafraîchir” + horodatage).
* L’enregistrer en `errorElement` du router **ou** wrapper racine.
  **Fini si**: une 500 simulée → affichage propre, pas de stacktrace.

---

### FC-P0-004 (BACK) — Cache persistant générique

**But**: instantané + never-empty.
**À faire**

* `backend/storage/`: `save_json(path, payload, meta)` + `load_json(path)` qui renvoient `{ data, meta:{last_update,source,version} }`.
* `backend/services/cache_layer.py`:

  ```py
  def load_or_compute(key, compute_fn, ttl=None):
      snap = load_json(key)
      if snap and fresh(snap, ttl): return snap
      data = compute_fn()
      return save_json(key, data, meta=…)
  ```
* Routes **news** et **forecasts**: utiliser `load_or_compute(...)`.
  **Fini si**: reboot du back → les réponses restent non-vides (dernier snapshot) + `last_update` présent (preuve via `curl`).

---

### FC-P0-010 (INFRA) — Hook pre-push = smoke

**But**: empêcher un push qui casse l’app.
**À faire**

* `scripts/smoke.sh`: 5 curls + `grep` clés (`ok`, `articles`, `rows`, etc.) → `exit 1` si échec.
* `git/hooks/pre-push` (doc: comment l’installer localement).
  **Fini si**: démo d’un push bloqué quand `/api/health` est KO.

---

### FC-P0-014 (BACK+UI) — Health+ enrichi - DONE

**But**: visibilité fraîcheur par domaine.
**Étapes complétées**

* `/api/health`: retourne `{ ok, backend_up, last_updates: {news,forecasts,weekly,backtests}, data_paths }`.
* Backend: Enhanced health endpoint with status, domain freshness info, and data paths.
  **Fini si**: `curl /api/health | jq` montre `last_updates.*`; badge visible sur le front.

**Completed by**: ALEX-FINANCE-ANALYST-SUPERMAN-29

**Files updated**:
- `/api/routes/health.py` - Enhanced health endpoint with backend status, domain freshness and data paths info

---

## Petites notes de mise au point

* **Contrat unique ≠ front multiple**: la doc backend impose `{ok,data}`. Harmonise *toute* la couche front sur cette enveloppe (pas d’exception locale), ou, si tu préfères aplatir côté front, fais-le via un **interceptor** qui renvoie déjà `res.data` (et adapte les composants en conséquence).




















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

