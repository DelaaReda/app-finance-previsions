# API Edge Routing Table (Strangler Progressif)

Ce document décrit la couche `platform/edge` ajoutée pour les endpoints critiques sans breaking change.

## Objectif
- conserver les routes publiques existantes,
- ajouter un contrat additif stable (`status`, `error`, `meta`),
- permettre un rollback instantané via feature flags.

## Feature Flags
- `FC_API_EDGE_FORECASTS=1`
- `FC_API_EDGE_RECOMMENDATIONS=1`
- `FC_API_EDGE_STOCKS=1`

Chaque flag peut être passé à `0` pour revenir au comportement legacy d’un endpoint.

## Table de routage critique
| Route publique | Handler actuel | Service domaine principal | Fallback | Flag |
|---|---|---|---|---|
| `/api/forecasts` | `domains/forecasts/api/forecasts.py:get_forecasts` | `domains/forecasts/application/forecasts_service.py` | payload vide never-empty + `status=degraded` | `FC_API_EDGE_FORECASTS` |
| `/api/recommendations/daily` | `platform/main.py:recommendations_daily` | `brief_weekly` + contexte market | recommandations vides + contexte neutre | `FC_API_EDGE_RECOMMENDATIONS` |
| `/api/stocks/{ticker}/sheet` | `platform/main.py:ticker_sheet` | `core.market_data` + `analytics.phase2_technical` | fiche ticker dégradée (structure stable) | `FC_API_EDGE_STOCKS` |

## Contrat additif (non-breaking)
Tous les endpoints ci-dessus gardent:
- `ok`
- `data`

Et ajoutent:
- `status`: `ok|degraded|error`
- `error`: objet structuré `{code, message, detail?}` ou `null`
- `meta`: `{source, freshness_s, request_id, schema_version, fallback, generated_at}`


## Bootstrap extraction status (2026-03-04)

- `platform/main.py` now mounts `platform/routers/health.py` for:
  - `/api/health`
  - `/api/freshness`
  - `/api/frontend/config`
- Additional router modules created for progressive extraction:
  - `macro`, `stocks`, `news`, `forecasts`, `brief`, `copilot`, `notes`, `rag`, `signals`.
- Public routes remain unchanged; extraction remains additive/non-breaking.

## 2026-03-05 Extraction status

- `platform/main.py` still hosts bootstrap + legacy helper logic; extraction continues route-by-route.
- Routing contract remains strict:
  - public path unchanged,
  - historical fields preserved,
  - `status/error/meta` kept additive only.
## Update 2026-03-06 — Critical Endpoint Gate Notes

- Critical endpoint smoke keeps strict contract checks on:
  - `/api/forecasts`
  - `/api/recommendations/daily`
  - `/api/stocks/{ticker}/sheet`
- `/api/stocks/{ticker}/sheet` now has cold-start tolerant retry before hard fail in smoke.
- Timeouts after retry are classified `DEGRADED` in smoke output to avoid false hard negatives.

Validation (VM):
```bash
cd /home/venom/analyse-financiere
scripts/critical_endpoints_smoke.sh --base-url http://3.98.20.77
scripts/runtime_e2e_gate.sh
```

Note:
- Use `http://3.98.20.77` from the UTM VM for public product API proof.
- Reserve `127.0.0.1:8050` for host-local app debugging when logged directly into the app host.

## 2026-03-06 Monitor API additions (non-edge, additive)

For runtime supervision, monitor now also exposes:
- `/api/agent-activity`
- `/api/tasks/active`
- `/api/dependencies/map`

These routes are observability-only and do not modify edge routing for product APIs.
