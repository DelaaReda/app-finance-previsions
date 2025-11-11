# UI/Front — Process Improvements (PO: NORA-11)

Objectif: accélérer delivery et qualité UI/Front avec une stack unifiée Mantine + Tremor (+ Tailwind utilitaire), en réduisant dettes et flakiness.

---

## 1) Definition of Done (UI)
- Design system unique (Mantine), Tremor pour dataviz, Tailwind utilitaire.
- 4 états par vue: Loading (Loader/Skeleton) • Empty (EmptyState) • Error (Alert/Notification) • Freshness (badge).
- Accès sûrs (`safeArray`, `safeGet`) — jamais de `.map` sur `undefined`.
- Accessibilité: focus visible, aria-labels sur actions, contraste OK.
- Tests E2E stables (selectors `data-testid`), screenshots avant/après.

## 2) Sélecteurs & Tests
- Ajouter `data-testid` sur nav, CTA, tableaux, filtres.
- Refactor tests Playwright pour n’utiliser que `data-testid`.
- Intégrer un smoke UI rapide dans le pre-push (en plus des API): charge `/`, `/macro`, `/forecasts` et vérifie au moins 1 composant clé présent.

## 3) Locks & Ownership clairs
- 1 tâche = 1 lock (`.locks/FC-XXX.lock`) avec `owner=@handle` + ETA.
- Petits lots mergeables (< 300 lignes modifiées) pour feedback rapide.

## 4) DRY & Architecture Front
- Unifier les clients API (un seul module), `API_BASE = env || '/api'`.
- Unifier helpers sûrs dans `@/lib/safe`; déprécier doublons.
- Design system: Mantine (v7) + Tremor; wrappers `src/ui/*` pour composants.
- Interdire MUI via ESLint `no-restricted-imports` (ban `@mui/*`).
- Centraliser composants statuts (`EmptyState`, `FreshnessBadge`, `ErrorBoundary`).

## 5) Rituels & Communication
- Avant dev: mini-spec (objectif, fichiers impactés, DoD, preuve).
- Pendant: message court de progression (blocage, risques).
- Fin: commit avec preuves (captures, log tests) et update `SCORE_AGENTS.md` si impact réel.

## 6) Budgets de Performance
- TTI initial < 300ms (local dev) sur Dashboard & Forecasts.
- Tables simples (Mantine/Table custom) ou pagination par défaut 25; lazy-loading des composants lourds.
- Pas de double design systems en prod (MUI interdit).

## 7) Accessibilité & i18n
- Utiliser `fr-FR` consistently pour dates; utilitaire date unique.
- Vérifier tab-navigabilité; aria-pressed/selected sur toggles.

## 8) Revue & Evidence
- PR/commit doivent inclure: DoD checké + preuves (screenshots, logs test) + chemins modifiés.
- Refuser merges sans Empty/Loading/Error/Freshness pris en charge.

---

Quick‑Wins (semaine 1)
- Enlever MUI; wrappers `src/ui/*` mappant Mantine; ESLint ban `@mui/*`.
- Normaliser `API_BASE` (client unique) et Safe helpers.
- Ajout `data-testid` dans nav + refactor sélecteurs tests.
