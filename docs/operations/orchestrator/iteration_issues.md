
---
## [OPEN] API Contract Schema Non-Conforme — 2026-03-04T12:22:55Z

**ID**: API-CONTRACT-001
**Sévérité**: HIGH
**Détecté par**: Architect audit (2026-03-04T12:22:55Z)
**Endpoints affectés**:
- `/api/forecasts?horizon=short&limit=24`
- `/api/recommendations/daily?limit=3`  
- `/api/stocks/AAPL/sheet`

**Problème**: Les endpoints retournent HTTP 200 avec `ok=true` et `data` mais manquent:
- `status` (doit être: "ok" | "degraded" | "error")
- `meta.source`
- `meta.request_id`
- `meta.schema_version`
- `meta.fallback`

**Impact**: `critical_endpoints_smoke.sh` échoue → fc_health_check affiche FAIL → admin génère fausse alerte `backend_unreachable` dans son contrat

**Action requise**: DEV doit ajouter middleware de réponse standard (`ResponseEnvelope`) à ces 3 routes ou les migrer vers le schema canonique.

**Preuve**: `bash scripts/critical_endpoints_smoke.sh` → exit 1

