# Sentry Debug Runbook (FastAPI + Frontend)

Objectif: debuguer Sentry de facon reproductible, en commencant par des tests simples qui valident le wiring avant d'analyser des incidents reels.

## 1) Ce qui est deja integre dans le repo

- Initialisation Sentry dans `src/api/main.py` avant `FastAPI()`.
- Variables supportees:
  - `SENTRY_DSN` (obligatoire pour activer Sentry)
  - `SENTRY_ENABLE_LOGS` (defaut: `true`)
  - `SENTRY_TRACES_SAMPLE_RATE` (defaut: `1.0` en debug / `0.2` hors debug)
  - `SENTRY_PROFILE_SESSION_SAMPLE_RATE` (defaut: `0.2` en debug / `0.0` hors debug)
  - `SENTRY_PROFILE_LIFECYCLE` (defaut: `trace`)
  - `SENTRY_PROFILES_SAMPLE_RATE` (fallback legacy)
  - `SENTRY_SEND_DEFAULT_PII` (defaut: `true`)
  - `SENTRY_ENVIRONMENT` (optionnel)
  - `SENTRY_RELEASE` (optionnel)
  - `FRONTEND_SENTRY_DSN` (optionnel, fallback vers `SENTRY_DSN`)
  - `FRONTEND_SENTRY_TRACES_SAMPLE_RATE` (defaut `SENTRY_TRACES_SAMPLE_RATE` ou `0.2`)
  - `FRONTEND_SENTRY_REPLAYS_SESSION_SAMPLE_RATE` (defaut `0.0`)
  - `FRONTEND_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE` (defaut `1.0`)
  - `trace_propagation_targets` frontend injecte via `/api/frontend/config`
- Route de verification:
  - `GET /sentry-debug` exposee seulement si:
    - `SENTRY_DSN` est defini
    - mode debug actif (`FINANCE_COPILOT_DEBUG=1`)
  - `GET /api/frontend/config` expose la config publique frontend (DSN + sampling)
  - Jobs instrumentes:
    - `news_ingest`, `news_sentiment`, `macro_series_snapshot`, `stocks_prices_refresh`,
      `judge_enrich`, `judge_quality_report`, `validate_and_generate_data`
    - Tags Sentry: `component=job`, `job.name=<nom_du_job>`

## 2) Ordre de test recommande (test first)

1. Validation config (DSN + dependances)
2. Validation backend locale (`/sentry-debug`)
3. Validation endpoint metier (erreurs non gerees)
4. Validation frontend (capture JS)
5. Correlation frontend -> backend dans Sentry

## 3) Preflight (a faire en premier)

Depuis `copilot-app/backend`:

```bash
.venv/bin/python -m pip show sentry-sdk
```

Configurer `.env`:

```env
SENTRY_DSN=https://<public_key>@o<org_id>.ingest.us.sentry.io/<project_id>
SENTRY_ENABLE_LOGS=true
SENTRY_TRACES_SAMPLE_RATE=1.0
SENTRY_PROFILE_SESSION_SAMPLE_RATE=1.0
SENTRY_PROFILE_LIFECYCLE=trace
SENTRY_SEND_DEFAULT_PII=true
SENTRY_ENVIRONMENT=dev
```

Important:
- Le backend est en mode strict: un DSN invalide fait echouer le demarrage (`BadDsn`).

## 4) Verifications executees dans ce repo

Tests de wiring executes localement avec `TestClient`:

- `SENTRY_DSN=''` + debug on -> `/sentry-debug` absent.
- `SENTRY_DSN` valide + debug on -> `/sentry-debug` present.
- Appel `/sentry-debug` -> status `500` (event + trace envoyes).
- `SENTRY_DSN` valide + debug off -> `/sentry-debug` absent.
- `SENTRY_DSN='abc123'` -> `BadDsn` au demarrage.

Conclusion:
- Le wiring est correct.
- Le mode strict fonctionne.

## 5) Scenarios backend a tester

### Scenario A: erreur non geree (doit remonter)

Route de test:

```python
@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0
```

Attendu:
- Event "ZeroDivisionError" dans Sentry
- Transaction associee dans Performance

### Scenario B: erreur geree (ne remonte pas par defaut)

Exemple:

```python
@app.get("/handled")
async def handled():
    try:
        1 / 0
    except ZeroDivisionError:
        return {"ok": False}
```

Attendu:
- Pas d'event automatique Sentry
- Si besoin: `sentry_sdk.capture_exception(e)` dans le bloc `except`

### Scenario C: erreurs 4xx metier (422/404)

Attendu:
- Pas d'event "exception" par defaut
- Transaction HTTP visible si tracing actif

### Scenario D: tache background / job

Dans un `except` job:

```python
import sentry_sdk

try:
    run_job()
except Exception as e:
    sentry_sdk.capture_exception(e)
    raise
```

Attendu:
- Event present meme hors requete HTTP

### Scenario E: logs et metrics Sentry

```python
import sentry_sdk
from sentry_sdk import metrics

sentry_sdk.logger.info("info log")
sentry_sdk.logger.warning("warning log")
metrics.count("checkout.failed", 1)
metrics.gauge("queue.depth", 42)
metrics.distribution("cart.amount_usd", 187.5)
```

Attendu:
- Logs visibles dans Sentry Logs
- Metrics visibles dans Sentry Metrics (apres delai court)

## 6) Scenarios frontend a tester

Ton frontend est statique (`frontend/app`) et charge deja `js/sentry-init.js`.

1. Verifier la config publique backend:
```bash
curl -s http://127.0.0.1:8050/api/frontend/config | jq
```
2. Ouvrir `http://localhost:5173`.
3. Dans la console navigateur, lancer:
```js
triggerFrontendSentryError()
```

Attendu:
- Event JS dans Sentry (projet frontend)
- Trace frontend visible

## 7) Correlation frontend <-> backend

Pour relier les traces:

- Frontend: activer tracing
- Backend: `SENTRY_TRACES_SAMPLE_RATE > 0`
- Autoriser les origins frontend dans CORS (deja present)

Verification:
- Depuis une action UI qui appelle l'API, verifier dans Sentry:
  - transaction frontend
  - span HTTP sortant
  - transaction backend correspondante

## 8) Endpoint de verification runtime

Si backend lance sur `8050`:

```bash
curl -i http://127.0.0.1:8050/sentry-debug
curl -s http://127.0.0.1:8050/api/frontend/config | jq
```

Attendu:
- `500 Internal Server Error`
- event visible dans Sentry en quelques secondes

## 9) Troubleshooting rapide

- `BadDsn` au demarrage:
  - DSN invalide ou incomplet
  - verifier le format complet `https://...@o....ingest.us.sentry.io/...`

- Pas d'event apres `/sentry-debug`:
  - verifier `SENTRY_DSN`
  - verifier acces reseau vers `*.sentry.io`
  - verifier que l'erreur est non geree ou explicitement `capture_exception`

- Pas de route `/sentry-debug`:
  - verifier `FINANCE_COPILOT_DEBUG=1`
  - verifier `SENTRY_DSN` non vide

- Frontend sans telemetry:
  - verifier `GET /api/frontend/config` -> `data.sentry.enabled=true`
  - verifier que `frontend/app/js/sentry-init.js` est charge dans `frontend/app/index.html`
  - verifier la console navigateur pour `[telemetry] Sentry frontend initialized`

## 10) Checklist incident

1. Verifier `release`, `environment`, `timestamp`
2. Filtrer par endpoint (`transaction`), status, exception type
3. Regarder breadcrumbs + payload + user/context
4. Reproduire localement avec route ou payload minimal
5. Corriger puis valider sur `/sentry-debug` et endpoint metier
