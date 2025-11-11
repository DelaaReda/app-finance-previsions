# UI Improvement Backlog — Mantine + Tremor (PO: NORA-11)

Mantine-first UI avec Tremor pour data viz et Tailwind utilitaire. Objectifs: cohérence visuelle, simplicité pour agents IA, never‑empty, a11y, performance.

Notation d’effort: S (≤0.5j), M (1–2j), L (3–5j)

---

## FC-UI-PO-001 — Navigation unique + sélecteurs stables
- Why: Ambiguïté Playwright (doublons « News »), 2 navs concurrentes.
- Scope: Archiver `src/App-with-ErrorBoundary.tsx`, garder `src/layout/AppShell.tsx`. Ajouter `data-testid` sur chaque item nav.
- Files: `copilot-app/frontend/webapp/src/layout/AppShell.tsx`, `copilot-app/frontend/webapp/src/App-with-ErrorBoundary.tsx`
- DoD: Un seul lien « News »; tests strict passent; `data-testid="nav-news"` présent.
- Proof: Screenshot nav + rapport test.
- Effort: S

## FC-UI-PO-002 — Base API DRY (env-aware)
- Why: `src/api/client.ts` ignore `VITE_API_BASE_URL`.
- Scope: `API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'` appliqué dans clients; doc `.env` ajustée.
- Files: `copilot-app/frontend/webapp/src/api/client.ts`, `copilot-app/frontend/webapp/src/services/api.ts`, `.env`
- DoD: App OK via proxy et base explicite; curl 5173/8050 OK.
- Proof: 2 curls + tests verts.
- Effort: S

## FC-UI-PO-003 — Unifier helpers sûrs (déprécier utils/safeAccess)
- Why: Duplication `@/utils/safeAccess.ts` vs `@/lib/safe.ts`.
- Scope: Migrer importations vers `@/lib/safe` (safeArray, safeGet, safeNumber, hasItems). Adapter appels.
- Files: Macro, Stocks, MarketBrief, TickerSheet, TopSignals, TopRisks.
- DoD: `rg '@/utils/safeAccess'` → 0; build OK.
- Proof: Tests UI passent.
- Effort: M

## FC-UI-PO-004 — Mantine standardisation Macro & Stocks (remove inline styles)
- Why: Inline styles lourds, lack d’homogénéité.
- Scope: Remplacer containers/sections par composants via `@/ui` (wrappers Mantine). Skeleton/Empty/Alert.
- Files: `src/pages/Macro.tsx`, `src/pages/Stocks.tsx`
- DoD: Plus d’inline styles majeurs; Skeleton sur chargement; EmptyState propre.
- Proof: Screenshots avant/après.
- Effort: M

## FC-UI-PO-005 — États actifs visibles sur Market Brief
- Why: Boutons « Quotidien/Hebdo » sans state visuel (QA v3).
- Scope: Tabs/Toggles Mantine via `@/ui`; `aria-pressed`.
- Files: `src/pages/MarketBrief.tsx`
- DoD: État actif évident; test aria passe.
- Proof: Screenshot + Playwright vert.
- Effort: S

## FC-UI-PO-006 — Accessibilité (A11y) minimum
- Why: Manque d’aria-labels & focus.
- Scope: Aria sur actions, focus ring Mantine, labels tables.
- Files: AppShell, Table, pages clés.
- DoD: Axe devtools sans erreurs critiques; clavier OK.
- Proof: Rapport axe.
- Effort: M

## FC-UI-PO-007 — Performance budget UI
- Why: Garder TTI initial < 300ms.
- Scope: Paginer 25, lazy‑load composants lourds, réduire bundles (supprimer MUI).
- Files: `src/components/*`, lazy imports.
- DoD: Perf Lighthouse stable; traces.
- Proof: Snapshot perf.
- Effort: M

## FC-UI-PO-008 — Patterns universels (Loading/Empty/Error/Freshness)
- Why: UX cohérente « never-empty ».
- Scope: Normaliser 4 états partout; centraliser (`EmptyState`, `FreshnessBadge`, notifications).
- Files: Dashboard, Macro, Stocks, News, Forecasts, Brief.
- DoD: 4 états présents; QA valide.
- Proof: Screenshots 4 états.
- Effort: M

## FC-UI-PO-009 — Wrappers UI (`src/ui/*`) + ESLint ban MUI
- Why: API stable simple pour agents IA; éviter imports directs.
- Scope: Créer `src/ui/*` mappant Mantine; ESLint no‑restricted‑imports bloque `@mui/*`.
- Files: `src/ui/*`, `.eslintrc.cjs`
- DoD: Pages importent via `@/ui`; `rg "@mui/"` → 0; build OK.
- Proof: Rapport ESLint + build.
- Effort: M

---

## Notes d’audit (références code)
- Navigation dupliquée: `copilot-app/frontend/webapp/src/App-with-ErrorBoundary.tsx:51–55`, `copilot-app/frontend/webapp/src/layout/AppShell.tsx:39–49`.
- Helpers dupliqués: `copilot-app/frontend/webapp/src/utils/safeAccess.ts:1–110` vs `copilot-app/frontend/webapp/src/lib/safe.ts:1–80`.
- Base API non standardisée: `copilot-app/frontend/webapp/src/api/client.ts:6–10` ignore env.
- Styles inline lourds: `copilot-app/frontend/webapp/src/pages/Macro.tsx:18–98`, `copilot-app/frontend/webapp/src/pages/Stocks.tsx:28–210`.

