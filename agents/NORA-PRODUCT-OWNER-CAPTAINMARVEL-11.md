# NORA-PRODUCT-OWNER-CAPTAINMARVEL-11

## Profil
- **Rôle** : Product Owner • UI/UX Designer senior
- **Super‑héros** : Captain Marvel
- **Mission** : Garder Finance Copilot aligné sur la vision produit (never-empty, Mantine/Tremor, fluide & testable)
- **Score** : 0 pts _(mise à jour après preuves visuelles / build complet)_

## Missions & Suivi

| Statue | Description | Preuve prévue |
| --- | --- | --- |
| ✅ Livré | Refactor Backtests UI (presets + interprétation Copilot) | Capture `/backtests` + log `pnpm run build` (à produire) |
| 🔄 En cours | Audit UI global & plan correctif | Ce document + update `TASKS_BOARD.md` |
| 🗓️ Planifié | Mise à niveau Forecasts/Macro/News vers hooks partagés | Tickets FC-UI-NEWS-HOOKS & co |

## Audit UI (05 février 2025)
- `copilot-app/frontend/webapp/src/pages/Forecasts.tsx:1`  
  ‣ Page encore branchée sur `useQuery + apiGet`. Contrat `FC-API-FORECASTS-REAL` incomplet (pas de `useForecasts`, pas de never-empty consolidé).  
  → Action: nouvelle tâche **FC-UI-NEWS-HOOKS** + revoir `FC-API-FORECASTS-REAL`.

- `copilot-app/frontend/webapp/src/components/news/NewsFeed.tsx:1`  
  ‣ Le composant attend `{ items, filters, loadMore }` alors que `useNews` renvoie un `UseQueryResult`. Résultat: crash runtime et 9 erreurs TypeScript.  
  → Tâche ajoutée: **FC-UI-NEWS-HOOKS** (P0).

- `copilot-app/frontend/webapp/src/components/ui/SourceTooltip.tsx:1`  
  ‣ Dépendances `@mui/material` / `@mui/icons-material` toujours présentes ⇒ incompatible avec Mantine, bloque tsc.  
  → Tâche ajoutée: **FC-UI-REMOVE-MUI** (P0).

- `copilot-app/frontend/webapp/src/config/env.ts:1`  
  ‣ `ImportMetaEnv` non typé ⇒ 3 erreurs TS récurrentes, casse CI.  
  → Tâche ajoutée: **FC-BUILD-ENV-TYPES** (P0).

- `copilot-app/frontend/webapp/src/pages/Backtests.tsx:1`  
  ‣ Nouveau layout OK (presets, insights) mais beaucoup de `style={...}`. À terme migrer vers composants Mantine (`Select`, `TextInput`, `Grid`) pour cohérence DS.  
  → À suivre après stabilisation hooks.

## Amélioration du workflow (lecture docs actuelle)
1. **Verrouiller la définition de Done UI**  
   - `docs/dev/UI_PROCESS_IMPROVEMENTS.md` rappelle 4 états + preuves. Les merges récents ne respectent pas la preuve (ex : `/news`).  
   - Proposition: checklist obligatoire dans PR template + capture systématique.

2. **Stopper les doubles design systems**  
   - ESLint `no-restricted-imports` n’est pas encore actée (cf. même doc).  
   - Action: intégrée dans **FC-UI-REMOVE-MUI** (ajouter règle + CI).

3. **Nettoyage typecheck avant tout merge**  
   - `pnpm run typecheck` échoue depuis plusieurs commits. Bloque QA.  
   - Action: inclure typecheck dans pre-push (doc `docs/dev/pre-push.md`) une fois tâches P0 réglées.

4. **Synchroniser Hooks & Pages**  
   - Les hooks partagés `useForecasts`, `useMacroSeries`, `useNews` existent (`copilot-app/frontend/webapp/src/hooks`). Pages ne les consomment pas.  
   - Action: sprint court pour migrer 3 pages + ajouter tests Playwright sur `data-testid`.

## Next Steps
- Préparer preuves (`pnpm run build`, capture `/backtests`) avant mise à jour `SCORE_AGENTS.md`.
- Coordonner avec devs pour implémenter tickets P0 fraîchement ajoutés.
