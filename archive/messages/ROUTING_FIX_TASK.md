
---

## FC-ROUTE-023 — Correction proxy Vite (Routing Frontend)

**Status**: CLAIMED by MICHEL-DATA-QUALITY-MANAGER-SPIDERMAN-23

**But**: Corriger le fichier vite.config.ts qui redirige les routes frontend vers le backend à tort, causant des erreurs "Not Found" sur les pages critiques.

**Fichiers**
* `copilot-app/frontend/webapp/vite.config.ts`
* `copilot-app/frontend/webapp/src/router.tsx` (potentiellement à vérifier)
* `docs/routing-best-practices.md`

**Étapes**
1. **Identification du problème**:
   - Le fichier `vite.config.ts` a des règles de proxy incorrectes aux lignes 44-78
   - Routes comme `/forecasts`, `/brief`, `/macro`, `/stocks`, `/news`, `/copilot` sont redirigées vers le backend
   - Ces routes sont des routes frontend gérées par React Router, pas des endpoints backend
   - Le backend retourne `{"detail":"Not Found"}` car ces endpoints n'existent pas côté backend

2. **Correction du proxy**:
   - Retirer les règles de proxy pour les routes purement frontend: `/forecasts`, `/brief`, `/macro`, `/stocks`, `/news`, `/copilot`
   - Conserver uniquement les proxy pour les endpoints API réels: `/api/*`, `/health`
   - S'assurer que React Router gère correctement les routes frontend

3. **Validation de la correction**:
   - Tester la navigation entre toutes les pages: Dashboard, Forecasts, News, Brief, Macro, Stocks, etc.
   - Vérifier que les appels API continuent à fonctionner via le proxy `/api`
   - Confirmer que les routes frontend ne causent plus le message "Not Found"

**DoD**
* Fichier `vite.config.ts` corrigé: seuls `/api/*` et `/health` sont redirigés au backend
* Navigation frontend fonctionnelle sur toutes les routes (forecasts, brief, macro, news, etc.)
* Appels API backend toujours fonctionnels via le proxy
* Aucune erreur "Not Found" due à mauvaise redirection de routes
* Tests de navigation passent
* Preuve de fonctionnement: captures d'écran des pages après correction

**Impact critique**: 
* Cette correction résoudra les problèmes de navigation sur les pages spécifiques 
* Permettra aux utilisateurs d'accéder correctement aux différentes sections de l'application
* Éliminera les erreurs de type "Not Found" non justifiées