# MVP_SCOPE.md

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
