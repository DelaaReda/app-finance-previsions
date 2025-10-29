# ADR-003 — UI Sans Appels Réseau (Lecture Partitions Uniquement)

**Date**: 2025-10-29
**Statut**: ✅ Accepté (Implémenté Sprint 1)
**Décideurs**: Équipe Dev
**Révision**: —

---

## Contexte

L'application Dash (UI) affiche forecasts, macro, news. Problème: **où fait-on les appels externes** (yfinance, FRED, g4f)?

**Deux approches possibles**:
1. **UI fait appels**: Callbacks Dash appellent `yfinance.download()` directement
2. **Agents font appels**: UI lit uniquement partitions écrites par agents

**Problèmes approche 1 (UI avec réseau)**:
- **Latency UI**: Chargement page lent (10-30s si yfinance slow)
- **Rate limits**: FRED limite 120 req/jour → UI peut épuiser quota en 1h (multi-users)
- **Erreurs UI**: Si API down → page crash (UX horrible)
- **Tests difficiles**: Tests UI nécessitent internet (CI flaky)
- **Duplication logique**: Même fetch yfinance dans UI + agents

**Question**: UI doit-elle faire appels réseau ou juste lire data locale?

---

## Décision

**UI Dash = LECTURE SEULE** (partitions locales uniquement).

### Règles
1. **Aucun appel réseau dans callbacks UI**: Pas de `yfinance`, `requests`, `FRED`, `g4f` dans `src/dash_app/`
2. **Agents = compute + réseau**: Agents (`src/agents/`) font tous appels externes, écrivent partitions
3. **UI = lecture + affichage + filtrage**: UI lit partitions via `read_parquet_latest()`, filtre, affiche
4. **Exceptions autorisées**:
   - Appels **localhost** OK (ex: `run_make()` appelle subprocess local)
   - Tests E2E peuvent fetch si `AF_ALLOW_INTERNET=1` (opt-in)

### Séparation Responsabilités
```
┌─────────────────────────────────────────────────────────────┐
│                      Agents (src/agents/)                   │
│  • Fetch APIs externes (yfinance, FRED, g4f)               │
│  • Compute (forecasts, backtests, metrics)                 │
│  • Write partitions (data/*/dt=YYYYMMDD/)                  │
│  • Schedule: cron/APScheduler                              │
└─────────────────┬───────────────────────────────────────────┘
                  │ Write partitions
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Layer (Partitions)                    │
│  • data/forecast/dt=*/, data/macro/dt=*/                   │
│  • Parquet + JSON                                           │
│  • Immutable (ADR-001)                                      │
└─────────────────┬───────────────────────────────────────────┘
                  │ Read partitions
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      UI Dash (src/dash_app/)                │
│  • Read partitions (read_parquet_latest)                   │
│  • Filter (watchlist, horizon, date range)                 │
│  • Display (tables, charts, cards)                         │
│  • NO network calls (yfinance, FRED, g4f)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Conséquences

### ✅ Positives
1. **Performance UI**: Pages load <500ms (read parquet = 10-50ms vs API call 1-10s)
2. **Robustesse**: API externes down → UI fonctionne (affiche dernières données)
3. **Rate limits**: UI n'épuise jamais quotas API (agents contrôlés, 1 run/day)
4. **Tests rapides**: Tests UI pas besoin internet → CI fast (< 30s), reproductible
5. **Offline dev**: Dev peut travailler sans internet (fixtures partitions commités)
6. **Zéro duplication**: 1 seul endroit fetch yfinance (agents), pas copié dans UI

### ⚠️ Négatives
1. **Latency fraîcheur**: Données UI potentiellement périmées (jusqu'à 24h si agents daily)
2. **Complexité orchestration**: Besoin scheduler agents (cron/APScheduler)
3. **Debugging**: Si UI vide, cause peut être "agent pas run" (pas évident pour user)
4. **Actions manuelles**: Bouton "Refresh" UI doit appeler `run_make()` (pas direct fetch)

### 🔧 Mitigations Négatives
- **Monitoring freshness**: Page `/agents` affiche dernière `dt` par resource → Reda sait si périmé
- **Actions manuelles**: Boutons "Relancer agent" sur `/integration_agents_health` → Reda peut forcer refresh
- **Empty states FR**: Si partition absente → Alert "Aucune donnée disponible. Agents pas encore exécutés."
- **Scheduler robuste**: APScheduler + systemd service → agents run automatiquement horaire/daily

---

## Alternatives Rejetées

### Alternative 1: UI fait appels réseau (full stack React-like)
**Approche**: Callbacks Dash appellent yfinance directement

**Rejet**:
- **Latency**: Page load 10-30s inacceptable
- **Rate limits**: FRED 120 req/jour épuisé en 1h si multi-users
- **Tests**: CI nécessite internet (flaky, slow)
- **Duplication**: Même fetch dans UI + agents

### Alternative 2: Cache Redis entre UI et APIs
**Approche**: UI appelle API → cache Redis → API externe

**Rejet**:
- **Complexité**: Setup Redis, TTL management
- **Dépendance**: Redis must run (vs simple file system)
- **Overhead**: Redis queries slower que read parquet (50ms vs 10ms)
- **Pas besoin**: Partitions = cache naturel (immutable, filesystem)

### Alternative 3: Hybrid (UI fait appels seulement si partition manquante)
**Approche**: UI essaie read partition, si absent → fetch API

**Rejet**:
- **Flaky**: Comportement non déterministe (fast si partition, slow si API)
- **Tests**: Toujours besoin internet (fallback path)
- **Duplication**: Logique fetch dupliquée UI + agents

---

## Implémentation

### Pattern UI (lecture)
```python
# src/dash_app/pages/dashboard.py
from src.tools.parquet_io import read_parquet_latest

def layout():
    # ✅ CORRECT: Read partition
    df = read_parquet_latest("data/forecast", "final.parquet")

    if df is None or df.empty:
        # Empty state FR
        return dbc.Alert("Aucune donnée de forecast disponible. Les agents n'ont pas encore été exécutés.", color="info")

    # Render table
    return dbc.Table.from_dataframe(df.head(10))
```

### Anti-pattern UI (réseau)
```python
# ❌ INCORRECT: UI fait appel réseau
import yfinance as yf

def layout():
    # ❌ INTERDIT
    ticker = yf.Ticker("NVDA")
    df = ticker.history(period="1y")
    # ...
```

### Pattern Agent (compute + write)
```python
# src/agents/equity_forecast_agent.py
import yfinance as yf
from datetime import datetime
from pathlib import Path

def run_once():
    # ✅ CORRECT: Agent fait appel réseau
    tickers = ["AAPL", "NVDA", "MSFT"]
    forecasts = []

    for ticker in tickers:
        data = yf.download(ticker, period="500d")  # yfinance call OK ici
        forecast = compute_momentum(data)
        forecasts.append(forecast)

    # Write partition
    dt = datetime.utcnow().strftime("%Y%m%d")
    outdir = Path("data/forecast") / f"dt={dt}"
    outdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(forecasts).to_parquet(outdir / "forecasts.parquet")
```

### Exception: Actions Manuelles UI
```python
# src/dash_app/pages/integration_agents_health.py
from src.tools.make import run_make

@callback(
    Output("equity-forecast-log", "children"),
    Input("equity-forecast-btn", "n_clicks")
)
def run_equity_forecast_manual(n):
    if n:
        # ✅ AUTORISÉ: Appel subprocess local (pas réseau)
        result = run_make("equity-forecast", timeout=900)
        return dbc.Alert(result["stdout"], color="info")
    return ""
```

---

## Validation

### Git Hooks (pre-push)
Bloquer commits violant règle:

```bash
# .githooks/pre-push
# Reject yfinance/requests in src/dash_app/
if git diff --cached --name-only | grep "^src/dash_app/" | xargs grep -l "yfinance\|requests\|g4f\.ChatCompletion"; then
    echo "ERROR: UI callbacks ne doivent pas faire d'appels réseau (yfinance, requests, g4f)"
    echo "Déplacer logique dans agents (src/agents/)"
    exit 1
fi
```

### Tests
- **`tests/ui/test_routes.py`**: Tous tests UI sans `AF_ALLOW_INTERNET` → doivent passer (fixtures partitions)
- **`tests/e2e/test_all_pages_e2e.py`**: Tests E2E utilisent fixtures `tests/fixtures/data/` (commités)

### Monitoring
- **Page `/observability`**:
  - Badge "UI Health" vert si Dash répond HTTP 200 < 1s
  - Badge "Freshness" vert si toutes partitions < 24h

---

## Exceptions Documentées

### 1. Subprocess locaux (`run_make`)
**Autorisé**: UI peut appeler `subprocess.run(["make", "target"])`

**Justification**: Pas de réseau, juste orchestration locale

**Exemple**: Boutons "Relancer agent" sur `/integration_agents_health`

### 2. Tests E2E opt-in (`AF_ALLOW_INTERNET=1`)
**Autorisé**: Tests integration peuvent fetch si env var set

**Justification**: Valider end-to-end avec vraies APIs (opt-in CI)

**Exemple**:
```python
@pytest.mark.skipif(not os.getenv("AF_ALLOW_INTERNET"), reason="Requires internet")
def test_equity_forecast_real_api():
    result = run_equity_forecast()
    assert len(result) > 0
```

### 3. Localhost APIs (futurs)
**Autorisé**: Si futur micro-service local (ex: `http://localhost:9000/api/forecasts`)

**Justification**: Pas d'appel externe, just inter-process

**Note**: Actuellement pas utilisé

---

## Notes

- **Inspiration**: Jamstack architecture (build time data fetch, runtime read static)
- **Analogie**: UI = frontend React SPA, Agents = backend API/workers
- **Bénéfice sécurité**: UI pas besoin credentials API (keys uniquement dans agents/.env)

---

## Références

- [Jamstack Architecture](https://jamstack.org/)
- [12 Factor App (VI. Processes)](https://12factor.net/processes)
- Issue initiale: #23 "UI lent (yfinance calls dans callbacks)"

---

**Révisions**:
- **v1.0** (2025-10-29): Décision initiale
