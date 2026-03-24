---
status: historical
last_verified: 2026-03-07
superseded_by:
  - /home/venom/analyse-financiere/docs/product/PRODUCT_VISION.md
  - /home/venom/analyse-financiere/docs/product/planning/BACKEND_FIRST_PRODUCT_BACKLOG.md
---

# MVP_SCOPE.md

Historical note:
- This file captures an older MVP boundary.
- It remains useful for historical scope comparison only.
- Use the canonical product vision and canonical backlog for current scope decisions.

## In Scope (v1)
- Backend démarrable en 1 commande
- Frontend statique accessible
- 5 endpoints stables:
  - `/api/health`
  - `/api/stocks/prices`
  - `/api/news/feed`
  - `/api/forecasts`
  - `/api/copilot/ask`
- Affichage clair fallback vs données réelles
- Smoke test local reproductible

## Out of Scope (v1)
- Refonte architecture globale
- CI/CD enterprise
- Observabilité SRE avancée
- Optimisation exhaustive de tous endpoints
- Nouvelles features complexes non MVP

## Success Criteria
- Redémarrage local fiable
- Aucun endpoint MVP en erreur 500 sur smoke test
- UI principale exploitable sans crash
