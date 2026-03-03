# Audit Post-Migration — Performance & Stabilité Runtime

Date: 2026-03-03  
Scope: runtime VM-first (`./finance-copilot.sh`), backend API (`:8050`), frontend statique (`:5173`)

## Résumé Exécutif

La migration a amélioré la **latence des endpoints API** (très rapide sur les routes core), mais la stabilité architecture reste pénalisée par trois régressions structurelles:

1. **Compatibilité runtime incomplète** (Python typing + imports legacy).
2. **Contrats d’API partiellement cassés** (routes attendues par l’UI indisponibles).
3. **Démarrage trop lourd** (pipeline data complet dans le chemin critique).

En l’état: système utilisable, mais non “production-ready” côté fiabilité contractuelle.

---

## Mesures Factuelles

## 1) Cold start (script officiel)

Commande:

```bash
/usr/bin/time -p ./finance-copilot.sh start
```

Résultat observé:

- `real 41.34`
- `user 3.84`
- `sys 1.87`

Interprétation:

- Le temps de boot est dominé par les jobs de refresh synchrones avant readiness.

## 2) Latence API (30 requêtes/endpoint)

Campagne:

- `/api/health`
- `/api/forecasts?horizon=short&limit=24`
- `/api/recommendations/daily?limit=3`
- `/api/brief/daily`
- `/api/stocks/SPY/sheet`

Résultats:

- `/api/health`: `ok=30/30`, `avg=0.0165s`, `p95=0.0251s`, `max=0.1283s`
- `/api/forecasts`: `ok=30/30`, `avg=0.0032s`, `p95=0.0037s`
- `/api/recommendations/daily`: `ok=30/30`, `avg=0.0034s`, `p95=0.0052s`
- `/api/brief/daily`: `ok=30/30`, `avg=0.0039s`, `p95=0.0057s`
- `/api/stocks/SPY/sheet`: `ok=0/30`, `ko=30/30` (404 constant)

Interprétation:

- Le moteur API répond vite.
- Le problème principal n’est pas la performance brute, mais le **contrat endpoint + dépendances runtime**.

## 3) Erreurs startup/requêtes (observées)

- `news_ingest.py`: `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`
  - signature concernée: `def parse_published_datetime(value: Any) -> datetime | None`
- `validate_and_generate_data.py`: `No module named 'jobs.forecasts'`
- `copilot.sh`: job référencé introuvable `jobs/judge_quality_report.py`
- `/api/stocks/SPY/sheet`: 404 avec détail `No module named 'research.scoring'`
- `/api/macro/series/latest`: 404 `Not Found`

## 4) Dette architecture (backend)

- Fichier monolithe: `apps/api/src/platform/main.py` = **5244 lignes**
- Annotations:
  - `@app.get`: **47**
  - `include_router(...)`: **23**

Interprétation:

- Coexistence “domain routers + legacy monolith endpoints” => risque de dérive de contrats et imports cassés.

---

## Diagnostic Causal

1. **Migration incomplète des alias/imports**
   - Nouvelles namespaces présentes (`domains/*`) mais des chemins legacy restent actifs (`research.scoring`, `jobs.forecasts`).

2. **Chemin critique de démarrage trop chargé**
   - Ingestion/news/macro/judge démarrent dans le `start` synchrone avant disponibilité complète.

3. **Contrat API non verrouillé**
   - Certaines routes attendues par l’UI ne sont pas garanties (`/api/macro/series/latest`, `/api/stocks/{ticker}/sheet` avec dépendances non résolues).

---

## Verdict

- **Performance API**: bonne
- **Stabilité fonctionnelle**: moyenne
- **Fiabilité contractuelle API/UI**: insuffisante
- **Priorité immédiate**: corriger imports/compat, restaurer endpoints cassés, réduire startup critical path

---

## Références techniques

- `apps/api/runtime/copilot.sh`
- `apps/api/runtime/bootstrap_backend_env.sh`
- `apps/api/src/platform/main.py`
- `apps/api/src/platform/legacy/jobs/news_ingest.py`
- `apps/api/src/platform/legacy/jobs/validate_and_generate_data.py`
- `apps/api/src/platform/routes/__init__.py`
