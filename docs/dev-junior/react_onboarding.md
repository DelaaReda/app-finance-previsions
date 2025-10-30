# React Onboarding — Junior Dev

Objectif
- Démarrer vite sur l’UI React en respectant nos conventions et en intégrant proprement avec Python (Flask/Dash `/api/*`).

Arborescence
- `webapp/` — Vite + TypeScript
  - `src/api/client.ts` — helpers `apiGet/apiPost` (header `X-Trace-Id`)
  - `src/app/providers.tsx` — React Query Provider + Devtools
  - `src/pages/*` — pages routées (Forecasts, LLMJudge, Dashboard, Backtests…)
  - `src/shared/types.d.ts` (à générer via OpenAPI) et `src/shared/schemas.ts` (zod, optionnel)

Run local
- Backend API: `make dash-restart-bg` → http://127.0.0.1:8050
- Frontend React: `make react-dev` → http://127.0.0.1:5173 (proxy `/api` → 8050)

Pattern page (extrait)
```tsx
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '../api/client'

export default function Dashboard() {
  const q = useQuery({
    queryKey: ['kpis'],
    queryFn: () => apiGet<{ last_forecast_dt?: string; forecasts_count: number }>(`/dashboard/kpis`)
  })
  if (q.isLoading) return <small>Chargement…</small>
  if (!q.data?.ok) return <small style={{color:'tomato'}}>{q.data?.error ?? 'Erreur'}</small>
  const d = q.data.data
  return <div>Dernière partition: {d.last_forecast_dt ?? 'n/a'} — lignes: {d.forecasts_count}</div>
}
```

API — contrats
- Source de vérité: `docs/api/openapi.yaml` (générer types: `npx openapi-typescript docs/api/openapi.yaml -o webapp/src/shared/types.d.ts`).
- Si l’endpoint n’est pas documenté, ajoutez‑le (schémas min, exemples) et ouvrez une PR.

Conventions UI
- FR d’abord, empty‑states explicites (ne jamais casser l’UI).
- Tables simples HTML au début; améliorer (virtualisation) si lignes > 1k.
- Pas de compute lourd côté UI; l’API prépare le minimum nécessaire.

Erreurs & Observabilité
- `X-Trace-Id` attaché via `api/client.ts`; corrélez avec logs Dash.
- State `loading/error` toujours visible; ne jamais masquer une erreur silencieusement.

Do / Don’t
- Do: valider responses (zod) sur les pages critiques.
- Do: réutiliser les endpoints existants avant d’en créer un.
- Don’t: appeler des scripts/shell depuis le navigateur; préférez un POST API côté Flask.

Checklist PR
- [ ] Types générés à jour (si OpenAPI évolue)
- [ ] Tests légers (render + interactions de base) ou capture d’écran
- [ ] README/PROGRESS mis à jour si fonctionnalité visible

