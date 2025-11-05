# Sprint V2 — High‑Impact Tasks (Spec + How‑To)

> But: Après stabilisation V1 (never‑empty + caching + UI safe), cette V2 focalise sur valeur produit (précision, fraîcheur, couverture) tout en restant fiable. Chaque tâche a Why, Inputs/Outputs, Steps, DoD.

Legend
- Area: UI, API, DATA, ML, OPS, SEC
- Effort: S (≤0.5j), M (1–2j), L (3–5j)

---

## V2‑UI‑MIGRATION — Mantine + Tremor unifiés (drop MUI)
- Area: UI
- Effort: M

Why
- Cohérence visuelle, simplicité pour agents IA, réduction des crashs et de la dette. Un seul design system: Mantine + Tremor (+ Tailwind utilitaire).

Steps
1) Interdire MUI via ESLint (`no-restricted-imports` sur `@mui/*`).
2) Créer `src/ui/*` wrappers autour de Mantine et refactor imports vers `@/ui`.
3) Remplacer composants MUI restants (News, Forecasts, Macro, Stocks) par Mantine.
4) Standardiser 4 états (Loading/Empty/Error/Freshness) et safe helpers (`@/lib/safe`).

DoD
- `rg "@mui/"` → 0; build OK.
- Pages clés fonctionnent via `@/ui`; tests Playwright passent.

---

## V2‑ML‑001 — Probabilistic Forecasts (Quantiles + Calibration)
- Area: ML, UI
- Effort: L

Why
- Les décisions ont besoin d’incertitude (bandes), pas d’un point unique.

Inputs/Outputs
- Input: features existantes (final.parquet construction).
- Output: `/api/forecasts` étendu avec `quantiles: { q10,q50,q90 }`, `calibration: {brier,ece}`.

Steps
1) Modèle: ajouter quantile regression (LightGBM quantile ou pinball via XGBoost) pour 3 quantiles.
2) Calibration: reliability diagram + isotonic/Platt pour proba directionnelle.
3) Materialisation: écrire `final.parquet` avec colonnes `{er_mean, q10,q50,q90, conf}`.
4) API: étendre schéma; backward‑compatible (champs optionnels).
5) UI: bandes de confiance sur Forecasts (remplissage entre q10–q90).

DoD
- Backtests: amélioration métrique pinball loss vs baseline.
- UI: bande q10–q90 visible; tooltip expliquant la confiance.

---

## V2‑ML‑002 — Regime & Drift Detection (HMM + Trigger)
- Area: ML, DATA
- Effort: M

Why
- Réduire dégradation modèle lors de changements de régime.

Steps
1) Construire HMM simple sur features (vol, slope, spread) → état {risk‑on, risk‑off, transition}.
2) Détection drift (PSI/KS) → flag si dépasse seuil.
3) Exposer `regime_state` et `drift_alert` dans `/api/health` + `/api/forecasts`.
4) Option: reweight signaux (meta‑learner) quand `risk‑off`.

DoD
- Alarme drift testable; logs clairs; KPI de reweight documenté.

---

## V2‑DATA‑001 — Filings & Transcripts (Ingestion + Résumés Cités)
- Area: DATA, NLP, UI
- Effort: L

Why
- Gains d’information majeurs (8‑K/10‑Q/10‑K, earnings calls) avec citations obligatoires.

Steps
1) Ingestion: SEC EDGAR (API) + earnings transcripts (public sources légales).
2) Normalisation: {ticker, filing_type, published_at, url, text} stockés Parquet.
3) Résumés LLM avec contraintes: “extract‑then‑summarize”, citations footnotes (url+timecode page).
4) API `/api/filings/search?ticker=...` et `/api/filings/summary?id=...`.
5) UI: onglet “Filings” dans Stocks + liens avec News.

DoD
- Au moins 2 tickers avec 10‑Q récents, résumés avec ≥2 citations.

---

## V2‑DATA‑002 — Alt‑Data (Options Flow, Short Interest)
- Area: DATA, ML
- Effort: L

Why
- Signaux directionnels complémentaires pour le scoring/ER.

Steps
1) Sources publiques/free tier (où possible) ou caches locaux.
2) Features: put/call ratio, net flow, changes short interest (% of float).
3) Joindre aux features modèle; tester impact via backtests.

DoD
- Colonnes alt‑data présentes dans `final.parquet`; UI affiche mini‑cards.

---

## V2‑API‑001 — Live Updates (SSE/WebSocket)
- Area: API, UI
- Effort: M

Why
- Eviter polling sur News/Stocks; améliorer réactivité.

Steps
1) SSE endpoint `/api/stream/news` (ping keep‑alive);
2) WebSocket `/api/ws/quotes` (si provider);
3) UI: hook `useSSE` + `useWS` avec fallback au polling.

DoD
- News se rafraîchit sans refresh; reconnection auto.

---

## V2‑OPS‑001 — OpenTelemetry + SLOs
- Area: OPS
- Effort: M

Why
- Mesurer latence/p95, freshness, erreurs par route.

Steps
1) Intégrer OTel (traces + metrics) au backend; exporter (stdout/prom).
2) Dash minimal Grafana/Prometheus (local compose) ou simple logs json.
3) Définir SLO: forecasts < 150ms cached; news freshness median < 15min.

DoD
- Dashboard latence + freshness; alertes simples si dépassement.

---

## V2‑BACKTEST‑001 — Walk‑Forward CV + Slippage
- Area: ML, DATA
- Effort: M

Steps
1) Walk‑forward splits (rolling windows) pour tuning.
2) Modéliser coûts & slippage (ex: 5–15 bps) selon liquidité.
3) Rapport OOS clair: perf, drawdown, turnover.

DoD
- Rapport enregistré dans `proofs/V2-BACKTEST/*`; amélioration vs baseline reportée.

---

## V2‑SEC‑001 — API Keys & Rate Limits Par Utilisateur
- Area: SEC, API, OPS
- Effort: M

Steps
1) Issuer local simple (tokens à usage dev); stockage chiffré.
2) Rate limit par clé & endpoint; logs d’audit.
3) UI: header `X-Api-Key` optionnel (dev mode auto attach).

DoD
- 429 gérés proprement; statistiques par clé dans `/api/health` (section sec).

---

## V2‑UI‑001 — Compare View + “What Changed?”
- Area: UI
- Effort: M

Steps
1) Page compare pour 2–4 tickers (scores, ER, risques, news liées).
2) “Since last run”: diff entre snapshots de forecasts (highlight).

DoD
- Page compare affichée, avec métriques clés et diff.

---

## V2‑GOV‑001 — Reproducibility & Lineage
- Area: OPS, DATA
- Effort: M

Steps
1) Manifests de run (code hash, data hash, seed, time) enregistrés.
2) Fonction `trace_id` propagée jusqu’aux artefacts.
3) README “how to reproduce” automatique par job.

DoD
- Run d’hier reproductible (mêmes artefacts) à ±epsilon.

---

Scoring Proposé (à ajuster par le manager)
- L: +140, M: +90, S: +50
- Bonus +30 si doc claire + preuves; +40 si perf → x2 vs baseline ; −100 si mock ; −80 si schema casse UI.
