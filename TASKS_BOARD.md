# 📣 MESSAGE AUX AGENTS — Lisez-moi et démarrez

Équipe, bienvenue dans **Finance Copilot**.
Ici on livre **du vrai**: zéro mock, zéro “quick fix” qui masque les problèmes.
Votre mission: **rendre l’app stable, rapide et alimentée par de la vraie data**.
Lisez les reviews : [text](reviews)
[➡️ Sprint V2 (plan détaillé prêt à l’emploi)](docs/product/SPRINT_V2_TASKS.md)
---

## 🔥 PRIORITY BOARD — Novembre 2025

### Legend
- Effort: S (≤0.5j) • M (1–2j) • L (3–5j)
- Tous les lots ⇒ **never-empty + preuves (curl/log + screenshot) dans `proofs/<TASK>`**

---

## P0 — Brancher la donnée réelle (immédiat)

#### FC-API-FORECASTS-REAL — Forecasts branchés backend *(Effort M)*
- **Why**: Remplacer les mocks par les vraies prévisions pour `/forecasts` (liste + détail).
- **Inputs**: `GET /api/forecasts`, `GET /api/forecasts/:id` (cf. spec ci-dessous).
- **Steps**:
  1. Implémenter `src/services/forecasts.ts` + `src/hooks/useForecasts.ts` (TanStack Query, ensureArray, fallback env).
  2. Brancher `Forecasts.tsx` (table + panneau détail) sur le hook, supprimer mock local.
  3. Bouton “Rafraîchir” qui refetch + badge Freshness alimenté par le payload backend.
- **DoD**:
  - Page affiche ≥1 ligne en mode backend, état vide propre quand aucun résultat.
  - `pnpm run typecheck` + `pnpm run build` OK.
  - Preuves: `curl /api/forecasts`, screenshots (liste + détail) dans `proofs/FC-API-FORECASTS-REAL/`.

#### FC-API-MACRO-REAL — Macro séries FRED/VIX *(Effort M)*
- **Why**: Les graphs macro doivent refléter CPI, VIX, 10Y-2Y, chômage réels.
- **Steps**:
  1. Service `fetchMacroSeries(codes)` + hook `useMacroSeries`.
  2. `Macro.tsx`: ring progress + charts Tremor alimentés par data réelle, sélecteur période (YTD/1Y/5Y).
  3. Badge Freshness + état vide/erreur soigné.
- **DoD**: Charts = data backend (aucune valeur en dur). Preuves: JSON `macro_series.json` + capture.

#### FC-API-NEWS-REAL — Flux news + sentiment *(Effort M)*
- **Why**: Fournir le flux agrégé backend (tickers, since, score) sans crash.
- **Steps**:
  1. Service `fetchNews` + hook `useNews` (support `VITE_USE_MOCKS`).
  2. `NewsFeed.tsx`: cartes avec sentiment chip, timeago, filtres actifs.
  3. Gestion erreurs, bouton “Charger plus” si backend le permet.
- **DoD**: `/news` affiche ≥5 articles réels, empty state propre, aucun `length` crash. Preuves: `curl /api/news` + screenshot.

---

## P1 — Copilot & Backtests (48–72h)

#### FC-COPILOT-SSE — Copilot streaming avec contexte *(Effort M)*
- **Why**: Offrir un copilote LLM contextualisé (prévision sélectionnée, filtres actifs).
- **Steps**:
  1. Implémenter `askCopilotSSE` (SSE ou fetch stream) + gestion abort.
  2. `Copilot.tsx`: zone chat, boutons rapides (“Explique la prévision”, “Risques & invalidation”), affichage streaming incremental.
  3. Gestion erreurs/réessai + log simple (optionnel) pour audits.
- **DoD**: Démo streaming (GIF/vidéo), transcript sauvegardé. Preuves: capture vidéo + log dans `proofs/FC-COPILOT-SSE/`.

#### FC-BACKTESTS-REAL — Résumé & equity curve *(Effort M)*
- **Why**: Montrer performance réelle (CAGR, maxDD, win rate, equity) pour les backtests.
- **Steps**:
  1. Service/hook `useBacktest(params)`.
  2. `Backtests.tsx`: cartes KPI + courbe Tremor + empty/erreur soigné, bouton “Recalculer”.
  3. Stocker JSON brut dans `proofs/` pour audit.
- **DoD**: KPI cohérents, courbe visible. Preuves: screenshot + JSON `backtest_<date>.json`.

---

## P2 — Hardening & Toggles (72–96h)

#### FC-MOCK-TOGGLE — Fallback mocks via env *(Effort S)*
- **Why**: Ne jamais casser l’UI si backend HS; dev rapide.
- **Steps**:
  1. Lire `VITE_USE_MOCKS` dans services, router vers MSW/mock si true.
  2. Documenter dans `docs/dev/ui_migration_mantine.md` (section “Mocks & SSE”).
- **DoD**: Mode mock ON sert des données locales sans crash; OFF = backend. Preuves: notes + capture.

#### FC-OBS-FRESHNESS — Harmoniser badges Freshness *(Effort S)*
- **Why**: Garantir cohérence freshness (forecasts, macro, news, backtests).
- **Steps**:
  1. Uniformiser `FreshnessBadge` (minutes + tooltip).
  2. Vérifier `/health` expose `last_updates` pour routes branchées.
- **DoD**: Badge indique minutes depuis dernier update (capture + log `/health`).

---

## P3 — Sprint V2 (ML / Data)

- **V2-ML-001 — Probabilistic Forecasts (Quantiles + Calibration)** *(L)*
- **V2-ML-002 — Regime & Drift Detection** *(M)*
- **V2-DATA-001 — Filings & Transcripts** *(L)*
- **V2-DATA-002 — Alt-Data (Options Flow, Short Interest)** *(L)*
- **V2-API-001 — Live Updates (SSE/WebSocket)** *(M)*
- **V2-OPS-001 — OpenTelemetry + SLOs** *(M)*

*Referencing docs/product/SPRINT_V2_TASKS.md pour détails ML/OPS.*

---

### Rappels DoD globaux
- Tests: `pnpm run typecheck` + `pnpm run build`.
- Smoke Playwright: `/`, `/forecasts`, `/macro`, `/news` (au moins composant clé rendu).
- Preuves à déposer dans `proofs/<TASK>/` (curl/log + screenshots ou GIF streaming).
- Documenter tout toggle/env dans `docs/dev/ui_migration_mantine.md` (ajouter section “Mocks & SSE”).
