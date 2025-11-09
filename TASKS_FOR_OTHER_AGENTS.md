# 📋 Tâches Détaillées pour Autres Agents Qwen

**Créé par**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Date**: 2025-01-27  
**But**: Fournir des tâches très détaillées et claires pour les agents Qwen moins expérimentés

---

## 🎯 Instructions Générales

### Avant de commencer
1. **Lire** `AGENTS.md` pour comprendre les règles du projet
2. **Vérifier** qu'aucun autre agent ne travaille sur la même tâche
3. **Tester** localement avec `./finance-copilot.sh start`
4. **Commit** avec votre nom et preuve de fonctionnement
5. **Mettre à jour** `SCORE_AGENTS.md` avec vos points

### Format de commit
```
feat(task-id): description courte @agentName (+points)
```

### Preuve requise
- Screenshot de la fonctionnalité
- Log curl de l'endpoint (si API)
- Test passant (si applicable)

---

## 🔥 PRIORITÉ P0 - Tâches Critiques

### TASK-QWEN-001 — Vérifier et compléter l'endpoint `/api/copilot/ask`

**Agent recommandé**: Agent backend Python  
**Points**: +80 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🔴 CRITIQUE

#### Contexte
La page Copilot frontend est implémentée mais l'endpoint backend doit être vérifié et complété.

#### Étapes détaillées

1. **Vérifier l'endpoint existant**
   ```bash
   # Chercher l'endpoint dans le code
   cd /mnt/utm/copilot-app/backend
   grep -r "/api/copilot/ask" .
   ```

2. **Lire le fichier contenant l'endpoint**
   - Probablement dans `backend/src/api/main.py` ou `backend/api/routes/copilot.py`
   - Vérifier si l'endpoint existe et fonctionne

3. **Tester l'endpoint**
   ```bash
   curl -X POST http://localhost:8050/api/copilot/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Quelle est la tendance du marché actuel?", "max_sources": 5}'
   ```

4. **Si l'endpoint n'existe pas ou est incomplet**:
   - Créer `backend/api/routes/copilot.py` (si n'existe pas)
   - Implémenter l'endpoint POST `/api/copilot/ask`
   - Structure de réponse attendue:
     ```python
     {
       "ok": True,
       "data": {
         "answer": "Réponse du LLM...",
         "sources": [
           {"title": "...", "url": "...", "relevance": 0.85}
         ],
         "confidence": 0.92
       }
     }
     ```

5. **Intégrer avec le service LLM**
   - Utiliser le service LLM existant (probablement `backend/services/llm_service.py`)
   - Intégrer avec RAG si disponible
   - Gérer les erreurs proprement

6. **Tester avec le frontend**
   - Démarrer le backend: `./finance-copilot.sh start`
   - Ouvrir http://localhost:5173/copilot
   - Poser une question et vérifier que la réponse arrive

#### DoD (Definition of Done)
- [ ] Endpoint `/api/copilot/ask` répond avec structure `{ok, data}`
- [ ] Test curl fonctionne et retourne une réponse
- [ ] Page Copilot frontend peut envoyer des questions
- [ ] Réponses LLM sont affichées correctement
- [ ] Gestion d'erreurs implémentée (never-empty pattern)
- [ ] Preuve: screenshot + log curl dans `proofs/TASK-QWEN-001/`

#### Fichiers à modifier/créer
- `backend/api/routes/copilot.py` (créer si n'existe pas)
- `backend/api/main.py` (ajouter router si nécessaire)
- `backend/services/llm_service.py` (vérifier/intégrer)

---

### TASK-QWEN-002 — Ajouter lazy loading à la page Macro

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 1h  
**Priorité**: 🟡 OPTIMISATION

#### Contexte
La page Macro utilise déjà des graphiques lazy-loaded dans les widgets, mais la page principale pourrait bénéficier d'optimisations supplémentaires.

#### Étapes détaillées

1. **Lire le fichier actuel**
   ```bash
   cat copilot-app/frontend/webapp/src/pages/Macro.tsx
   ```

2. **Identifier les composants à lazy-load**
   - Vérifier quels composants sont importés directement
   - Identifier les composants lourds (graphiques, tableaux)

3. **Appliquer React.lazy()**
   ```typescript
   // Avant
   import MacroBoardWidget from '@/components/widgets/MacroBoardWidget';
   
   // Après
   import { lazy, Suspense } from 'react';
   const MacroBoardWidget = lazy(() => 
     import('@/components/widgets/MacroBoardWidget').then(m => ({ default: m.default }))
   );
   ```

4. **Ajouter Suspense boundaries**
   ```typescript
   <Suspense fallback={<Skeleton height={400} radius="md" />}>
     <MacroBoardWidget />
   </Suspense>
   ```

5. **Vérifier le chargement**
   - Ouvrir DevTools → Network
   - Recharger la page Macro
   - Vérifier que les composants se chargent de manière différée

#### DoD
- [ ] Tous les composants lourds sont lazy-loaded
- [ ] Suspense boundaries avec skeletons appropriés
- [ ] Bundle initial réduit (vérifier dans DevTools)
- [ ] Page charge sans erreur
- [ ] Preuve: screenshot DevTools Network + bundle size

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/pages/Macro.tsx`

---

### TASK-QWEN-003 — Améliorer la gestion d'erreurs dans Stocks.tsx

**Agent recommandé**: Agent frontend React  
**Points**: +30 pts  
**Effort estimé**: 1h  
**Priorité**: 🟡 STABILITÉ

#### Contexte
La page Stocks doit avoir une gestion d'erreurs robuste pour éviter les crashes.

#### Étapes détaillées

1. **Lire le fichier actuel**
   ```bash
   cat copilot-app/frontend/webapp/src/pages/Stocks.tsx
   ```

2. **Vérifier la gestion d'erreurs actuelle**
   - Chercher les `useQuery` hooks
   - Vérifier si `error` est géré
   - Vérifier si `isLoading` est géré

3. **Ajouter ErrorBoundary si nécessaire**
   ```typescript
   import { ErrorBoundary } from 'react-error-boundary';
   
   function ErrorFallback({error}: {error: Error}) {
     return (
       <Alert color="red" title="Erreur">
         {error.message}
       </Alert>
     );
   }
   ```

4. **Améliorer les états d'erreur dans les hooks**
   ```typescript
   const { data, isLoading, error } = useQuery({
     queryKey: ['stocks-search', query],
     queryFn: async () => {
       try {
         return await stocksService.search(query);
       } catch (err) {
         // Log l'erreur mais ne pas crasher
         console.error('Stocks search error:', err);
         return { ok: false, data: [], error: err.message };
       }
     }
   });
   ```

5. **Ajouter des états Empty/Error dans l'UI**
   ```typescript
   if (error) {
     return <Alert color="red">Erreur lors de la recherche</Alert>;
   }
   
   if (!isLoading && !data?.length) {
     return <EmptyState title="Aucun résultat" />;
   }
   ```

#### DoD
- [ ] Tous les `useQuery` gèrent les erreurs
- [ ] ErrorBoundary en place si nécessaire
- [ ] États Empty/Error affichés proprement
- [ ] Aucun crash même si API échoue
- [ ] Preuve: screenshot avec erreur simulée

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/pages/Stocks.tsx`

---

## 🟡 PRIORITÉ P1 - Tâches Importantes

### TASK-QWEN-004 — Ajouter tests E2E pour la page Dashboard

**Agent recommandé**: Agent test/QA  
**Points**: +50 pts  
**Effort estimé**: 3-4h  
**Priorité**: 🟡 QUALITÉ

#### Contexte
La page Dashboard est critique mais n'a pas de tests E2E.

#### Étapes détaillées

1. **Vérifier la structure de tests existante**
   ```bash
   ls -la copilot-app/frontend/webapp/tests/
   ```

2. **Créer un test Playwright**
   ```typescript
   // tests/e2e/dashboard.spec.ts
   import { test, expect } from '@playwright/test';
   
   test('Dashboard loads correctly', async ({ page }) => {
     await page.goto('http://localhost:5173/');
     
     // Vérifier que la page charge
     await expect(page.locator('h1')).toBeVisible();
     
     // Vérifier que les KPIs sont affichés
     await expect(page.locator('[data-testid="dashboard-kpis"]')).toBeVisible();
   });
   ```

3. **Ajouter des tests pour les widgets**
   - Vérifier que les widgets se chargent
   - Vérifier que les données sont affichées
   - Vérifier les états de chargement

4. **Exécuter les tests**
   ```bash
   cd copilot-app/frontend/webapp
   npm run test:e2e
   ```

#### DoD
- [ ] Test E2E pour Dashboard créé
- [ ] Tests passent localement
- [ ] Tests vérifient les KPIs, widgets, et données
- [ ] Preuve: log des tests passants

#### Fichiers à créer
- `copilot-app/frontend/webapp/tests/e2e/dashboard.spec.ts`

---

### TASK-QWEN-005 — Optimiser les imports dans vite.config.ts

**Agent recommandé**: Agent frontend build/optimization  
**Points**: +30 pts  
**Effort estimé**: 1h  
**Priorité**: 🟡 PERFORMANCE

#### Contexte
Le fichier `vite.config.ts` a déjà du code splitting, mais peut être optimisé davantage.

#### Étapes détaillées

1. **Lire le fichier actuel**
   ```bash
   cat copilot-app/frontend/webapp/vite.config.ts
   ```

2. **Analyser le bundle actuel**
   ```bash
   cd copilot-app/frontend/webapp
   npm run build
   npm run preview
   # Ouvrir DevTools → Network et analyser les bundles
   ```

3. **Optimiser manualChunks**
   - Regrouper les dépendances par usage
   - Séparer les vendors lourds (Tremor, Mantine)
   - Créer des chunks par route si nécessaire

4. **Vérifier la taille des bundles**
   - Bundle initial < 200KB (idéal)
   - Chunks séparés pour routes lourdes

#### DoD
- [ ] Bundle initial optimisé
- [ ] Chunks logiques créés
- [ ] Taille des bundles réduite
- [ ] Preuve: screenshot DevTools avec tailles de bundles

#### Fichiers à modifier
- `copilot-app/frontend/webapp/vite.config.ts`

---

## 📝 Tâches de Documentation

### TASK-QWEN-006 — Documenter les patterns utilisés dans les sprints

**Agent recommandé**: Agent documentation  
**Points**: +40 pts  
**Effort estimé**: 2h  
**Priorité**: 🟢 DOCUMENTATION

#### Contexte
Les 5 sprints ont utilisé des patterns importants (lazy loading, caching, never-empty) qui doivent être documentés.

#### Étapes détaillées

1. **Créer un document de patterns**
   ```bash
   mkdir -p copilot-app/docs/patterns
   touch copilot-app/docs/patterns/LAZY_LOADING.md
   touch copilot-app/docs/patterns/CACHING.md
   touch copilot-app/docs/patterns/NEVER_EMPTY.md
   ```

2. **Documenter chaque pattern**
   - Exemples de code
   - Quand l'utiliser
   - Bonnes pratiques
   - Anti-patterns à éviter

3. **Ajouter des exemples concrets**
   - Extraire des exemples des sprints complétés
   - Montrer avant/après

#### DoD
- [ ] 3 documents de patterns créés
- [ ] Exemples de code inclus
- [ ] Bonnes pratiques documentées
- [ ] Liens depuis README principal

#### Fichiers à créer
- `copilot-app/docs/patterns/LAZY_LOADING.md`
- `copilot-app/docs/patterns/CACHING.md`
- `copilot-app/docs/patterns/NEVER_EMPTY.md`

---

## 🎯 Comment Choisir une Tâche

1. **Lisez** toutes les tâches disponibles
2. **Choisissez** une tâche qui correspond à vos compétences
3. **Vérifiez** qu'aucun autre agent ne travaille dessus
4. **Créez** un fichier de tracking (ex: `QWEN-AGENT-NAME.md`)
5. **Marquez** la tâche comme "CLAIMED" dans ce fichier
6. **Commencez** le travail

---

---

## 🔥 PRIORITÉ P0 - Tâches Critiques (Suite)

### TASK-QWEN-007 — Implémenter endpoint `/api/stocks/prices` avec support range

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 2h  
**Priorité**: 🔴 CRITIQUE

#### Contexte
L'endpoint `/api/stocks/prices` existe mais ignore le paramètre `range`, ce qui limite son utilité.

#### Étapes détaillées

1. **Vérifier l'endpoint actuel**
   ```bash
   cd /mnt/utm/copilot-app/backend
   grep -r "/api/stocks/prices" .
   ```

2. **Lire le code de l'endpoint**
   - Probablement dans `backend/api/routes/stocks.py`
   - Vérifier comment le paramètre `range` est géré

3. **Implémenter le support range**
   ```python
   @router.get("/stocks/prices")
   def get_stock_prices(
       ticker: str = Query(..., description="Stock ticker"),
       range: str = Query("1mo", description="Time range: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max")
   ):
       # Utiliser yfinance avec le paramètre range
       stock = yf.Ticker(ticker)
       hist = stock.history(period=range)
       # Retourner les données formatées
   ```

4. **Tester l'endpoint**
   ```bash
   curl "http://localhost:8050/api/stocks/prices?ticker=AAPL&range=1y"
   ```

#### DoD
- [ ] Endpoint accepte et utilise le paramètre `range`
- [ ] Test curl avec différents ranges fonctionne
- [ ] Données retournées correspondent au range demandé
- [ ] Preuve: logs curl avec différents ranges

#### Fichiers à modifier
- `backend/api/routes/stocks.py`

---

### TASK-QWEN-008 — Améliorer la page LLMJudge avec composants Mantine

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2h  
**Priorité**: 🟡 AMÉLIORATION

#### Contexte
La page LLMJudge fonctionne mais utilise des composants basiques. Il faut la polir avec Mantine.

#### Étapes détaillées

1. **Lire le fichier actuel**
   ```bash
   cat copilot-app/frontend/webapp/src/pages/LLMJudge.tsx
   ```

2. **Identifier les améliorations**
   - Remplacer les composants basiques par Mantine
   - Ajouter PageHeader pour cohérence
   - Améliorer l'affichage des résultats
   - Ajouter des états de chargement/erreur

3. **Appliquer les améliorations**
   ```typescript
   // Ajouter PageHeader
   <PageHeader
     title="LLM Judge"
     icon={<IconScale size={28} />}
     description="Évaluation des modèles LLM pour prévisions"
   />
   
   // Améliorer l'affichage des résultats avec Cards Mantine
   // Ajouter des badges pour les statuts
   // Ajouter des progress bars pour les métriques
   ```

4. **Tester la page**
   - Ouvrir http://localhost:5173/judge
   - Vérifier que tout s'affiche correctement

#### DoD
- [ ] PageHeader ajouté
- [ ] Composants Mantine utilisés partout
- [ ] États Loading/Error gérés
- [ ] UI cohérente avec le reste de l'app
- [ ] Preuve: screenshot avant/après

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/pages/LLMJudge.tsx`

---

### TASK-QWEN-009 — Ajouter tests unitaires pour les hooks React

**Agent recommandé**: Agent test/QA  
**Points**: +60 pts  
**Effort estimé**: 3-4h  
**Priorité**: 🟡 QUALITÉ

#### Contexte
Les hooks React (useForecasts, useNews, etc.) n'ont pas de tests unitaires.

#### Étapes détaillées

1. **Vérifier la structure de tests**
   ```bash
   ls -la copilot-app/frontend/webapp/tests/
   ```

2. **Créer un test pour useForecasts**
   ```typescript
   // tests/hooks/useForecasts.test.ts
   import { renderHook, waitFor } from '@testing-library/react';
   import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
   import { useForecasts } from '@/hooks/useForecasts';
   
   test('useForecasts fetches data correctly', async () => {
     const queryClient = new QueryClient();
     const wrapper = ({ children }) => (
       <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
     );
     
     const { result } = renderHook(() => useForecasts({ horizon: '1mo' }), { wrapper });
     
     await waitFor(() => expect(result.current.isSuccess).toBe(true));
     expect(result.current.data).toBeDefined();
   });
   ```

3. **Créer des tests pour d'autres hooks**
   - useNews
   - useMacroSeries
   - useStocksSearch

4. **Exécuter les tests**
   ```bash
   cd copilot-app/frontend/webapp
   npm run test
   ```

#### DoD
- [ ] Tests pour au moins 3 hooks créés
- [ ] Tests passent
- [ ] Coverage > 70% pour les hooks
- [ ] Preuve: log des tests passants

#### Fichiers à créer
- `copilot-app/frontend/webapp/tests/hooks/useForecasts.test.ts`
- `copilot-app/frontend/webapp/tests/hooks/useNews.test.ts`
- `copilot-app/frontend/webapp/tests/hooks/useMacroSeries.test.ts`

---

### TASK-QWEN-010 — Nettoyer les imports inutilisés dans api/main.py

**Agent recommandé**: Agent backend Python  
**Points**: +30 pts  
**Effort estimé**: 30min  
**Priorité**: 🟢 MAINTENANCE

#### Contexte
Le fichier `api/main.py` contient des imports inutilisés qui polluent le code.

#### Étapes détaillées

1. **Identifier les imports inutilisés**
   ```bash
   cd /mnt/utm/copilot-app/backend
   # Utiliser un linter ou analyser manuellement
   python -m pylint api/main.py | grep "unused-import"
   ```

2. **Vérifier chaque import**
   - Chercher dans le fichier si l'import est utilisé
   - Si non utilisé, le retirer

3. **Vérifier que rien ne casse**
   ```bash
   # Tester que l'API démarre toujours
   ./finance-copilot.sh start
   # Vérifier les endpoints principaux
   curl http://localhost:8050/api/health
   ```

#### DoD
- [ ] Tous les imports inutilisés retirés
- [ ] API démarre sans erreur
- [ ] Aucune régression
- [ ] Preuve: diff avant/après

#### Fichiers à modifier
- `backend/api/main.py` ou `backend/src/api/main.py`

---

### TASK-QWEN-011 — Ajouter PageHeader à toutes les pages manquantes

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 1-2h  
**Priorité**: 🟡 COHÉRENCE UI

#### Contexte
Toutes les pages doivent avoir un PageHeader pour la cohérence UI.

#### Étapes détaillées

1. **Identifier les pages sans PageHeader**
   ```bash
   cd copilot-app/frontend/webapp/src/pages
   grep -L "PageHeader" *.tsx
   ```

2. **Ajouter PageHeader à chaque page**
   ```typescript
   import PageHeader from '@/components/layout/PageHeader';
   
   export default function MyPage() {
     return (
       <Container size="xl" py="xl">
         <PageHeader
           title="Titre de la page"
           icon={<IconName size={28} />}
           description="Description de la page"
         />
         {/* Reste du contenu */}
       </Container>
     );
   }
   ```

3. **Vérifier chaque page**
   - Ouvrir chaque page dans le navigateur
   - Vérifier que le PageHeader s'affiche correctement

#### DoD
- [ ] Toutes les pages ont un PageHeader
- [ ] PageHeader cohérent (même style)
- [ ] Icônes appropriées pour chaque page
- [ ] Preuve: screenshot de chaque page

#### Fichiers à modifier
- Tous les fichiers dans `copilot-app/frontend/webapp/src/pages/` sans PageHeader

---

### TASK-QWEN-012 — Implémenter le système de refresh global

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Un bouton "Refresh All" devrait rafraîchir toutes les données du Dashboard.

#### Étapes détaillées

1. **Créer un contexte RefreshContext**
   ```typescript
   // src/contexts/RefreshContext.tsx
   import { createContext, useContext } from 'react';
   
   const RefreshContext = createContext<{
     refreshAll: () => void;
   }>({ refreshAll: () => {} });
   
   export const useRefresh = () => useContext(RefreshContext);
   ```

2. **Implémenter le provider**
   - Utiliser React Query's `queryClient.invalidateQueries()`
   - Invalider toutes les queries en une fois

3. **Ajouter le bouton au Dashboard**
   ```typescript
   <Button onClick={refreshAll}>
     <IconRefresh /> Refresh All
   </Button>
   ```

4. **Tester**
   - Cliquer sur "Refresh All"
   - Vérifier que toutes les données se rafraîchissent

#### DoD
- [ ] RefreshContext créé
- [ ] Bouton "Refresh All" fonctionnel
- [ ] Toutes les queries se rafraîchissent
- [ ] Feedback visuel pendant le refresh
- [ ] Preuve: vidéo/screenshot du refresh

#### Fichiers à créer
- `copilot-app/frontend/webapp/src/contexts/RefreshContext.tsx`

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`

---

### TASK-QWEN-013 — Ajouter des métriques de performance (latency tracking)

**Agent recommandé**: Agent backend Python  
**Points**: +50 pts  
**Effort estimé**: 2h  
**Priorité**: 🟡 MONITORING

#### Contexte
Il faut tracker la latence des endpoints API pour identifier les problèmes de performance.

#### Étapes détaillées

1. **Créer un middleware de tracking**
   ```python
   # backend/api/middleware/performance.py
   import time
   from fastapi import Request
   
   @app.middleware("http")
   async def track_latency(request: Request, call_next):
       start_time = time.time()
       response = await call_next(request)
       latency = time.time() - start_time
       response.headers["X-Response-Time"] = str(latency)
       return response
   ```

2. **Ajouter le middleware à main.py**
   ```python
   from api.middleware.performance import track_latency
   app.middleware("http")(track_latency)
   ```

3. **Tester**
   ```bash
   curl -I http://localhost:8050/api/health
   # Vérifier le header X-Response-Time
   ```

#### DoD
- [ ] Middleware créé
- [ ] Header X-Response-Time ajouté à toutes les réponses
- [ ] Latence mesurée correctement
- [ ] Preuve: log curl avec header

#### Fichiers à créer
- `backend/api/middleware/performance.py`

#### Fichiers à modifier
- `backend/api/main.py`

---

### TASK-QWEN-014 — Créer un composant ErrorBoundary réutilisable

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 1-2h  
**Priorité**: 🟡 STABILITÉ

#### Contexte
Un ErrorBoundary centralisé améliorerait la gestion d'erreurs.

#### Étapes détaillées

1. **Créer le composant ErrorBoundary**
   ```typescript
   // src/components/errors/ErrorBoundary.tsx
   import { Component, ErrorInfo, ReactNode } from 'react';
   import { Alert, Button, Stack, Text } from '@mantine/core';
   
   interface Props {
     children: ReactNode;
     fallback?: ReactNode;
   }
   
   interface State {
     hasError: boolean;
     error?: Error;
   }
   
   export class ErrorBoundary extends Component<Props, State> {
     // Implémenter componentDidCatch et render
   }
   ```

2. **Ajouter au App.tsx**
   ```typescript
   <ErrorBoundary>
     <Routes>
       {/* routes */}
     </Routes>
   </ErrorBoundary>
   ```

3. **Tester**
   - Simuler une erreur
   - Vérifier que l'ErrorBoundary capture l'erreur

#### DoD
- [ ] ErrorBoundary créé
- [ ] Intégré dans App.tsx
- [ ] Affiche un message d'erreur clair
- [ ] Bouton de retry si applicable
- [ ] Preuve: screenshot avec erreur capturée

#### Fichiers à créer
- `copilot-app/frontend/webapp/src/components/errors/ErrorBoundary.tsx`

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/App.tsx`

---

### TASK-QWEN-015 — Ajouter des skeletons pour tous les états de chargement

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 2h  
**Priorité**: 🟡 UX

#### Contexte
Tous les composants qui chargent des données devraient avoir des skeletons.

#### Étapes détaillées

1. **Identifier les composants sans skeletons**
   ```bash
   cd copilot-app/frontend/webapp/src
   grep -r "isLoading" --include="*.tsx" | grep -v "Skeleton"
   ```

2. **Créer des skeletons appropriés**
   ```typescript
   // Utiliser les composants Skeleton de Mantine
   {isLoading ? (
     <Stack>
       <Skeleton height={50} radius="md" />
       <Skeleton height={200} radius="md" />
     </Stack>
   ) : (
     // Contenu réel
   )}
   ```

3. **Appliquer à tous les composants**
   - Dashboard widgets
   - Tables de données
   - Graphiques

#### DoD
- [ ] Tous les composants avec isLoading ont des skeletons
- [ ] Skeletons appropriés (taille, forme)
- [ ] UX améliorée (pas de flash de contenu)
- [ ] Preuve: screenshot avec skeletons

#### Fichiers à modifier
- Tous les composants avec isLoading dans `src/components/` et `src/pages/`

---

### TASK-QWEN-016 — Implémenter le système de cache HTTP côté backend

**Agent recommandé**: Agent backend Python  
**Points**: +50 pts  
**Effort estimé**: 2h  
**Priorité**: 🟡 PERFORMANCE

#### Contexte
Certains endpoints devraient avoir des headers HTTP de cache pour réduire les requêtes.

#### Étapes détaillées

1. **Créer un helper pour les headers de cache**
   ```python
   # backend/api/middleware/cache.py
   from fastapi import Response
   from datetime import datetime, timedelta
   
   def add_cache_headers(response: Response, max_age: int = 3600):
       response.headers["Cache-Control"] = f"public, max-age={max_age}"
       response.headers["ETag"] = f'"{hash(str(response.body))}"'
       return response
   ```

2. **Appliquer aux endpoints appropriés**
   - `/api/macro/series` (déjà fait partiellement)
   - `/api/dashboard/kpis`
   - `/api/news/feed` (pour données anciennes)

3. **Tester**
   ```bash
   curl -I http://localhost:8050/api/macro/series
   # Vérifier les headers Cache-Control et ETag
   ```

#### DoD
- [ ] Helper créé
- [ ] Headers ajoutés à au moins 3 endpoints
- [ ] Cache fonctionne (vérifier avec curl)
- [ ] Preuve: log curl avec headers

#### Fichiers à créer
- `backend/api/middleware/cache.py`

#### Fichiers à modifier
- `backend/api/routes/macro.py`
- `backend/api/routes/dashboard.py`
- `backend/api/routes/news.py`

---

### TASK-QWEN-017 — Ajouter des tooltips informatifs sur les métriques

**Agent recommandé**: Agent frontend React  
**Points**: +30 pts  
**Effort estimé**: 1h  
**Priorité**: 🟢 UX

#### Contexte
Les utilisateurs ne comprennent pas toujours ce que signifient les métriques affichées.

#### Étapes détaillées

1. **Identifier les métriques sans explication**
   - KPIs du Dashboard
   - Métriques de backtests
   - Scores de robustesse

2. **Ajouter des Tooltips Mantine**
   ```typescript
   <Tooltip label="CAGR: Compound Annual Growth Rate - Taux de croissance annuel composé">
     <Text>CAGR: {value}%</Text>
   </Tooltip>
   ```

3. **Créer un composant MetricWithTooltip**
   ```typescript
   export function MetricWithTooltip({ 
     label, 
     value, 
     tooltip 
   }: { 
     label: string; 
     value: string; 
     tooltip: string 
   }) {
     return (
       <Tooltip label={tooltip}>
         <Text>{label}: {value}</Text>
       </Tooltip>
     );
   }
   ```

#### DoD
- [ ] Tooltips ajoutés à au moins 10 métriques
- [ ] Explications claires et utiles
- [ ] Tooltips fonctionnent (hover)
- [ ] Preuve: screenshot avec tooltip visible

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/components/widgets/*.tsx`
- `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`

---

### TASK-QWEN-018 — Créer un système de logging structuré côté backend

**Agent recommandé**: Agent backend Python  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 OBSERVABILITÉ

#### Contexte
Un système de logging structuré faciliterait le debugging et le monitoring.

#### Étapes détaillées

1. **Configurer le logging structuré**
   ```python
   # backend/core/logging_config.py
   import logging
   import json
   from datetime import datetime
   
   class StructuredFormatter(logging.Formatter):
       def format(self, record):
           log_data = {
               "timestamp": datetime.utcnow().isoformat(),
               "level": record.levelname,
               "message": record.getMessage(),
               "module": record.module,
               "function": record.funcName,
           }
           return json.dumps(log_data)
   ```

2. **Appliquer à tous les modules**
   ```python
   logger = logging.getLogger(__name__)
   logger.info("Endpoint called", extra={"endpoint": "/api/forecasts", "user": "anonymous"})
   ```

3. **Tester**
   - Faire des requêtes API
   - Vérifier les logs structurés

#### DoD
- [ ] Formatter structuré créé
- [ ] Logging appliqué à au moins 5 modules
- [ ] Logs au format JSON
- [ ] Preuve: exemple de log structuré

#### Fichiers à créer
- `backend/core/logging_config.py`

#### Fichiers à modifier
- `backend/api/routes/*.py` (ajouter logging)

---

### TASK-QWEN-019 — Ajouter des validations Pydantic strictes pour les endpoints

**Agent recommandé**: Agent backend Python  
**Points**: +40 pts  
**Effort estimé**: 1-2h  
**Priorité**: 🟡 SÉCURITÉ

#### Contexte
Les endpoints doivent valider strictement les entrées pour éviter les erreurs.

#### Étapes détaillées

1. **Créer des modèles Pydantic stricts**
   ```python
   # backend/api/models/forecasts.py
   from pydantic import BaseModel, Field, validator
   
   class ForecastFilter(BaseModel):
       horizon: str = Field(..., regex="^(1d|5d|1mo|3mo|6mo|1y|all)$")
       min_confidence: float = Field(0.0, ge=0.0, le=1.0)
       
       @validator('horizon')
       def validate_horizon(cls, v):
           if v not in ['1d', '5d', '1mo', '3mo', '6mo', '1y', 'all']:
               raise ValueError('Invalid horizon')
           return v
   ```

2. **Appliquer aux endpoints**
   - `/api/forecasts`
   - `/api/stocks/search`
   - `/api/news/feed`

3. **Tester avec des entrées invalides**
   ```bash
   curl "http://localhost:8050/api/forecasts?horizon=invalid"
   # Devrait retourner une erreur 422
   ```

#### DoD
- [ ] Modèles Pydantic créés pour au moins 3 endpoints
- [ ] Validations strictes en place
- [ ] Erreurs 422 pour entrées invalides
- [ ] Preuve: curl avec entrée invalide

#### Fichiers à créer
- `backend/api/models/forecasts.py`
- `backend/api/models/stocks.py`
- `backend/api/models/news.py`

---

### TASK-QWEN-020 — Créer une page de santé système (Health Check UI)

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 MONITORING

#### Contexte
Une page UI pour visualiser l'état de santé du système serait utile.

#### Étapes détaillées

1. **Créer la page Health**
   ```typescript
   // src/pages/Health.tsx
   import { useQuery } from '@tanstack/react-query';
   import { apiGet } from '@/api/client';
   
   export default function HealthPage() {
     const { data } = useQuery({
       queryKey: ['health'],
       queryFn: () => apiGet('/api/health'),
     });
     
     // Afficher les métriques de santé
   }
   ```

2. **Afficher les métriques**
   - Statut des endpoints
   - Latence des requêtes
   - Utilisation mémoire/CPU (si disponible)
   - Dernière mise à jour des données

3. **Ajouter des badges de statut**
   - Vert: OK
   - Jaune: Warning
   - Rouge: Error

#### DoD
- [ ] Page Health créée
- [ ] Affiche les métriques de santé
- [ ] Badges de statut fonctionnels
- [ ] Accessible via `/health`
- [ ] Preuve: screenshot de la page

#### Fichiers à créer/modifier
- `copilot-app/frontend/webapp/src/pages/Health.tsx` (peut exister déjà)

---

## 📊 Suivi des Tâches

| Tâche | Agent | Status | Points | Date |
|-------|-------|--------|--------|------|
| TASK-QWEN-001 | - | AVAILABLE | +80 | - |
| TASK-QWEN-002 | - | AVAILABLE | +40 | - |
| TASK-QWEN-003 | - | AVAILABLE | +30 | - |
| TASK-QWEN-004 | - | AVAILABLE | +50 | - |
| TASK-QWEN-005 | - | AVAILABLE | +30 | - |
| TASK-QWEN-006 | - | AVAILABLE | +40 | - |
| TASK-QWEN-007 | - | AVAILABLE | +60 | - |
| TASK-QWEN-008 | - | AVAILABLE | +50 | - |
| TASK-QWEN-009 | - | AVAILABLE | +60 | - |
| TASK-QWEN-010 | - | AVAILABLE | +30 | - |
| TASK-QWEN-011 | - | AVAILABLE | +40 | - |
| TASK-QWEN-012 | - | AVAILABLE | +50 | - |
| TASK-QWEN-013 | - | AVAILABLE | +50 | - |
| TASK-QWEN-014 | - | AVAILABLE | +40 | - |
| TASK-QWEN-015 | - | AVAILABLE | +40 | - |
| TASK-QWEN-016 | - | AVAILABLE | +50 | - |
| TASK-QWEN-017 | - | AVAILABLE | +30 | - |
| TASK-QWEN-018 | - | AVAILABLE | +50 | - |
| TASK-QWEN-019 | - | AVAILABLE | +40 | - |
| TASK-QWEN-020 | - | AVAILABLE | +50 | - |

---

## 🟢 PRIORITÉ P2 - Tâches d'Amélioration (Suite)

### TASK-QWEN-021 — Implémenter endpoint `/api/signals/top` (Top 3 signaux/risques)

**Agent recommandé**: Agent backend Python  
**Points**: +70 pts  
**Effort estimé**: 3-4h  
**Priorité**: 🟡 FEATURE

#### Contexte
L'endpoint `/api/signals/top` est déclaré mais retourne 501 (Not Implemented). Il doit retourner les Top 3 signaux et Top 3 risques.

#### Étapes détaillées

1. **Vérifier l'endpoint actuel**
   ```bash
   cd /mnt/utm/copilot-app/backend
   grep -r "/api/signals/top" .
   ```

2. **Créer le service de scoring composite**
   ```python
   # backend/services/signals_service.py
   def get_top_signals_and_risks():
       # Calculer score composite: 40% macro + 40% tech + 20% news
       # Trier par score
       # Retourner Top 3 signaux (score positif) et Top 3 risques (score négatif)
   ```

3. **Implémenter l'endpoint**
   ```python
   @router.get("/signals/top")
   def get_top_signals():
       signals = get_top_signals_and_risks()
       return ok({
           "top_signals": signals[:3],
           "top_risks": risks[:3],
           "composite_score": score
       })
   ```

4. **Tester**
   ```bash
   curl http://localhost:8050/api/signals/top
   ```

#### DoD
- [ ] Endpoint implémenté et fonctionnel
- [ ] Retourne Top 3 signaux et Top 3 risques
- [ ] Score composite calculé (40/40/20)
- [ ] Test curl fonctionne
- [ ] Preuve: log curl + screenshot

#### Fichiers à créer
- `backend/services/signals_service.py`

#### Fichiers à modifier
- `backend/api/routes/signals.py` (créer si n'existe pas)

---

### TASK-QWEN-022 — Implémenter endpoint `/api/brief/daily` et `/api/brief/weekly`

**Agent recommandé**: Agent backend Python  
**Points**: +80 pts  
**Effort estimé**: 4-5h  
**Priorité**: 🟡 FEATURE

#### Contexte
Les endpoints de brief sont déclarés mais retournent 501. Il faut implémenter la génération de briefs quotidiens et hebdomadaires.

#### Étapes détaillées

1. **Vérifier les endpoints**
   ```bash
   grep -r "/api/brief" .
   ```

2. **Créer le service de génération de brief**
   ```python
   # backend/services/brief_service.py
   def generate_daily_brief(universe: List[str]):
       # Agréger données: forecasts, news, macro
       # Générer résumé exécutif
       # Extraire Top 3 signaux/risques
       # Retourner structure complète
   
   def generate_weekly_brief(universe: List[str]):
       # Même logique mais sur 7 jours
   ```

3. **Implémenter les endpoints**
   ```python
   @router.get("/brief/daily")
   def get_daily_brief(universe: Optional[str] = None):
       brief = generate_daily_brief(universe.split(',') if universe else [])
       return ok(brief)
   ```

4. **Tester**
   ```bash
   curl "http://localhost:8050/api/brief/daily?universe=SPY,QQQ"
   curl "http://localhost:8050/api/brief/weekly?universe=SPY,QQQ"
   ```

#### DoD
- [ ] Endpoints implémentés
- [ ] Génération de briefs fonctionnelle
- [ ] Top 3 signaux/risques inclus
- [ ] Tests curl fonctionnent
- [ ] Preuve: JSON de brief généré

#### Fichiers à créer
- `backend/services/brief_service.py`

#### Fichiers à modifier
- `backend/api/routes/brief.py` (créer si n'existe pas)

---

### TASK-QWEN-023 — Ajouter export CSV/Excel pour les tableaux de données

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2h  
**Priorité**: 🟡 FEATURE

#### Contexte
Les utilisateurs veulent exporter les données des tableaux (forecasts, stocks, news) en CSV/Excel.

#### Étapes détaillées

1. **Créer un utilitaire d'export**
   ```typescript
   // src/utils/exportData.ts
   export function exportToCSV(data: any[], filename: string) {
     const csv = convertToCSV(data);
     const blob = new Blob([csv], { type: 'text/csv' });
     const url = URL.createObjectURL(blob);
     const a = document.createElement('a');
     a.href = url;
     a.download = filename;
     a.click();
   }
   ```

2. **Ajouter des boutons d'export**
   - Page Forecasts
   - Page Stocks
   - Page News
   - Tableaux de backtests

3. **Tester**
   - Cliquer sur "Export CSV"
   - Vérifier que le fichier se télécharge

#### DoD
- [ ] Utilitaire d'export créé
- [ ] Boutons d'export ajoutés à au moins 3 pages
- [ ] Export CSV fonctionnel
- [ ] Fichiers téléchargés correctement
- [ ] Preuve: screenshot avec fichier téléchargé

#### Fichiers à créer
- `copilot-app/frontend/webapp/src/utils/exportData.ts`

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/pages/Forecasts.tsx`
- `copilot-app/frontend/webapp/src/pages/Stocks.tsx`
- `copilot-app/frontend/webapp/src/pages/News.tsx`

---

### TASK-QWEN-024 — Créer un système de favoris/watchlist pour les tickers

**Agent recommandé**: Agent fullstack  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Les utilisateurs veulent sauvegarder leurs tickers favoris pour un accès rapide.

#### Étapes détaillées

1. **Backend: Créer endpoint watchlist**
   ```python
   # backend/api/routes/watchlist.py
   @router.post("/watchlist/add")
   def add_to_watchlist(ticker: str):
       # Sauvegarder dans localStorage backend ou DB
   
   @router.get("/watchlist")
   def get_watchlist():
       # Retourner liste des tickers favoris
   ```

2. **Frontend: Créer hook et composant**
   ```typescript
   // src/hooks/useWatchlist.ts
   export function useWatchlist() {
     // Gérer ajout/suppression de tickers
   }
   
   // src/components/watchlist/WatchlistWidget.tsx
   // Afficher les tickers favoris avec prix en temps réel
   ```

3. **Intégrer au Dashboard**
   - Ajouter widget Watchlist
   - Bouton "Add to Watchlist" sur page Stocks

#### DoD
- [ ] Endpoints watchlist créés
- [ ] Hook useWatchlist fonctionnel
- [ ] Widget Watchlist affiché
- [ ] Ajout/suppression fonctionne
- [ ] Preuve: screenshot avec watchlist

#### Fichiers à créer
- `backend/api/routes/watchlist.py`
- `frontend/webapp/src/hooks/useWatchlist.ts`
- `frontend/webapp/src/components/watchlist/WatchlistWidget.tsx`

---

### TASK-QWEN-025 — Ajouter des graphiques de comparaison multi-tickers

**Agent recommandé**: Agent frontend React  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre de comparer plusieurs tickers sur un même graphique.

#### Étapes détaillées

1. **Créer composant ComparisonChart**
   ```typescript
   // src/components/charts/ComparisonChart.tsx
   import { LineChart } from '@tremor/react';
   
   export function ComparisonChart({ tickers }: { tickers: string[] }) {
     // Fetch données pour chaque ticker
     // Normaliser les prix (base 100)
     // Afficher sur même graphique
   }
   ```

2. **Créer page Compare**
   ```typescript
   // src/pages/Compare.tsx
   // Sélecteur multi-tickers
   // Graphique de comparaison
   // Tableau de métriques comparées
   ```

3. **Ajouter route**
   - `/compare` dans le router

#### DoD
- [ ] Composant ComparisonChart créé
- [ ] Page Compare créée
- [ ] Comparaison de 2+ tickers fonctionne
- [ ] Graphique normalisé (base 100)
- [ ] Preuve: screenshot avec comparaison

#### Fichiers à créer
- `frontend/webapp/src/components/charts/ComparisonChart.tsx`
- `frontend/webapp/src/pages/Compare.tsx`

---

### TASK-QWEN-026 — Implémenter le système de notifications/alertes

**Agent recommandé**: Agent fullstack  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 FEATURE

#### Contexte
Les utilisateurs veulent être alertés quand certains événements se produisent (prix seuil, news importante, etc.).

#### Étapes détaillées

1. **Backend: Créer endpoints alertes**
   ```python
   # backend/api/routes/alerts.py
   @router.post("/alerts/create")
   def create_alert(alert_config: AlertConfig):
       # Sauvegarder configuration d'alerte
   
   @router.get("/alerts")
   def get_alerts():
       # Retourner alertes actives
   ```

2. **Backend: Job de vérification**
   ```python
   # backend/jobs/alert_checker.py
   def check_alerts():
       # Vérifier toutes les alertes
       # Déclencher si conditions remplies
   ```

3. **Frontend: UI de gestion**
   - Page Alerts
   - Formulaire de création
   - Liste des alertes actives

#### DoD
- [ ] Endpoints alertes créés
- [ ] Job de vérification fonctionne
- [ ] UI de gestion créée
- [ ] Création d'alerte fonctionne
- [ ] Preuve: screenshot avec alertes

#### Fichiers à créer
- `backend/api/routes/alerts.py`
- `backend/jobs/alert_checker.py`
- `frontend/webapp/src/pages/Alerts.tsx`

---

### TASK-QWEN-027 — Ajouter un système de recherche globale (Command Palette amélioré)

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Améliorer le Command Palette existant avec recherche globale (tickers, news, forecasts).

#### Étapes détaillées

1. **Vérifier le Command Palette existant**
   ```bash
   find . -name "*CommandPalette*" -o -name "*command*palette*"
   ```

2. **Créer service de recherche globale**
   ```typescript
   // src/services/globalSearch.ts
   export async function globalSearch(query: string) {
     // Rechercher dans: tickers, news, forecasts
     // Retourner résultats groupés par type
   }
   ```

3. **Améliorer Command Palette**
   - Ajouter recherche globale
   - Afficher résultats groupés
   - Navigation vers résultats

#### DoD
- [ ] Service de recherche globale créé
- [ ] Command Palette amélioré
- [ ] Recherche multi-sources fonctionne
- [ ] Navigation vers résultats fonctionne
- [ ] Preuve: screenshot avec recherche

#### Fichiers à modifier
- `frontend/webapp/src/components/system/CommandPalette.tsx`

#### Fichiers à créer
- `frontend/webapp/src/services/globalSearch.ts`

---

### TASK-QWEN-028 — Créer un système de thèmes personnalisables (dark/light/custom)

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 2h  
**Priorité**: 🟢 UX

#### Contexte
Permettre aux utilisateurs de choisir entre thème clair, sombre, ou personnalisé.

#### Étapes détaillées

1. **Créer ThemeProvider**
   ```typescript
   // src/contexts/ThemeContext.tsx
   export const ThemeProvider = ({ children }) => {
     const [theme, setTheme] = useState('light');
     // Gérer thème Mantine
   }
   ```

2. **Ajouter sélecteur de thème**
   - Dans le header/navbar
   - Options: Light, Dark, Auto (système)

3. **Persister le choix**
   - localStorage pour sauvegarder préférence

#### DoD
- [ ] ThemeProvider créé
- [ ] Sélecteur de thème fonctionnel
- [ ] Thèmes light/dark fonctionnent
- [ ] Préférence persistée
- [ ] Preuve: screenshot avec thèmes

#### Fichiers à créer
- `frontend/webapp/src/contexts/ThemeContext.tsx`

#### Fichiers à modifier
- `frontend/webapp/src/App.tsx`

---

### TASK-QWEN-029 — Ajouter des animations et transitions fluides

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 2h  
**Priorité**: 🟢 UX

#### Contexte
Améliorer l'UX avec des animations subtiles et transitions fluides.

#### Étapes détaillées

1. **Installer framer-motion**
   ```bash
   cd copilot-app/frontend/webapp
   npm install framer-motion
   ```

2. **Ajouter animations aux composants**
   ```typescript
   import { motion } from 'framer-motion';
   
   <motion.div
     initial={{ opacity: 0, y: 20 }}
     animate={{ opacity: 1, y: 0 }}
     transition={{ duration: 0.3 }}
   >
     {/* Contenu */}
   </motion.div>
   ```

3. **Animer les transitions de page**
   - Fade in/out
   - Slide transitions

#### DoD
- [ ] framer-motion installé
- [ ] Animations ajoutées à au moins 5 composants
- [ ] Transitions de page fluides
- [ ] Performance maintenue (pas de lag)
- [ ] Preuve: vidéo avec animations

#### Fichiers à modifier
- Composants dans `src/components/` et `src/pages/`

---

### TASK-QWEN-030 — Créer un système de raccourcis clavier

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 2h  
**Priorité**: 🟢 UX

#### Contexte
Permettre la navigation et actions via raccourcis clavier.

#### Étapes détaillées

1. **Installer react-hotkeys-hook**
   ```bash
   npm install react-hotkeys-hook
   ```

2. **Créer hook useKeyboardShortcuts**
   ```typescript
   // src/hooks/useKeyboardShortcuts.ts
   export function useKeyboardShortcuts() {
     useHotkeys('ctrl+k', () => openCommandPalette());
     useHotkeys('ctrl+/', () => showHelp());
     // etc.
   }
   ```

3. **Ajouter aide visuelle**
   - Modal avec liste des raccourcis
   - Accessible via `?` ou `Ctrl+/`

#### DoD
- [ ] Raccourcis clavier fonctionnels
- [ ] Au moins 5 raccourcis implémentés
- [ ] Aide visuelle disponible
- [ ] Documentation des raccourcis
- [ ] Preuve: screenshot avec aide

#### Fichiers à créer
- `frontend/webapp/src/hooks/useKeyboardShortcuts.ts`

---

### TASK-QWEN-031 — Ajouter des métriques de performance frontend (Web Vitals)

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 MONITORING

#### Contexte
Tracker les métriques de performance frontend (LCP, FID, CLS) pour identifier les problèmes.

#### Étapes détaillées

1. **Installer web-vitals**
   ```bash
   npm install web-vitals
   ```

2. **Créer service de tracking**
   ```typescript
   // src/services/performance.ts
   import { getCLS, getFID, getLCP } from 'web-vitals';
   
   export function trackWebVitals() {
     getCLS(console.log);
     getFID(console.log);
     getLCP(console.log);
   }
   ```

3. **Afficher dans DevDebugPanel**
   - Ajouter section Performance
   - Afficher métriques en temps réel

#### DoD
- [ ] web-vitals installé
- [ ] Métriques trackées
- [ ] Affichage dans DevDebugPanel
- [ ] Logs de performance disponibles
- [ ] Preuve: screenshot avec métriques

#### Fichiers à créer
- `frontend/webapp/src/services/performance.ts`

#### Fichiers à modifier
- `frontend/webapp/src/debug/DevDebugPanel.tsx`

---

### TASK-QWEN-032 — Créer un système de cache Redis côté backend

**Agent recommandé**: Agent backend Python  
**Points**: +80 pts  
**Effort estimé**: 4-5h  
**Priorité**: 🟡 PERFORMANCE

#### Contexte
Implémenter un cache Redis pour améliorer les performances des endpoints.

#### Étapes détaillées

1. **Installer redis-py**
   ```bash
   pip install redis
   ```

2. **Créer service de cache**
   ```python
   # backend/services/cache_service.py
   import redis
   
   redis_client = redis.Redis(host='localhost', port=6379)
   
   def get_from_cache(key: str):
       return redis_client.get(key)
   
   def set_to_cache(key: str, value: str, ttl: int = 3600):
       redis_client.setex(key, ttl, value)
   ```

3. **Intégrer aux endpoints**
   - Vérifier cache avant calcul
   - Mettre en cache après calcul

#### DoD
- [ ] Redis installé et configuré
- [ ] Service de cache créé
- [ ] Cache intégré à au moins 3 endpoints
- [ ] Performance améliorée (mesurée)
- [ ] Preuve: logs de cache + métriques

#### Fichiers à créer
- `backend/services/cache_service.py`

#### Fichiers à modifier
- `backend/api/routes/*.py` (intégrer cache)

---

### TASK-QWEN-033 — Ajouter rate limiting aux endpoints API

**Agent recommandé**: Agent backend Python  
**Points**: +50 pts  
**Effort estimé**: 2h  
**Priorité**: 🟡 SÉCURITÉ

#### Contexte
Protéger l'API contre les abus avec du rate limiting.

#### Étapes détaillées

1. **Installer slowapi**
   ```bash
   pip install slowapi
   ```

2. **Créer middleware de rate limiting**
   ```python
   # backend/api/middleware/rate_limit.py
   from slowapi import Limiter, _rate_limit_exceeded_handler
   from slowapi.util import get_remote_address
   
   limiter = Limiter(key_func=get_remote_address)
   
   @app.middleware("http")
   async def rate_limit_middleware(request, call_next):
       # Appliquer rate limiting
   ```

3. **Configurer les limites**
   - 100 req/min pour endpoints généraux
   - 10 req/min pour endpoints lourds (LLM, backtests)

#### DoD
- [ ] slowapi installé
- [ ] Rate limiting configuré
- [ ] Limites appliquées aux endpoints
- [ ] Erreurs 429 retournées si limite dépassée
- [ ] Preuve: curl avec rate limit test

#### Fichiers à créer
- `backend/api/middleware/rate_limit.py`

#### Fichiers à modifier
- `backend/api/main.py`

---

### TASK-QWEN-034 — Créer un système de backup automatique des données

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FIABILITÉ

#### Contexte
Sauvegarder automatiquement les données critiques (forecasts, briefs, etc.).

#### Étapes détaillées

1. **Créer script de backup**
   ```python
   # backend/scripts/backup_data.py
   def backup_data():
       # Copier fichiers JSON/Parquet
       # Compresser en archive
       # Sauvegarder avec timestamp
   ```

2. **Intégrer au scheduler**
   ```python
   # backend/scheduler/app.py
   scheduler.add_job(backup_data, "cron", hour=2)  # 2h du matin
   ```

3. **Créer endpoint de restauration**
   ```python
   @router.post("/admin/restore")
   def restore_backup(backup_file: str):
       # Restaurer depuis backup
   ```

#### DoD
- [ ] Script de backup créé
- [ ] Backup automatique configuré
- [ ] Archives créées avec timestamp
- [ ] Endpoint de restauration créé
- [ ] Preuve: fichier backup créé

#### Fichiers à créer
- `backend/scripts/backup_data.py`

#### Fichiers à modifier
- `backend/scheduler/app.py`

---

### TASK-QWEN-035 — Ajouter des tests d'intégration API avec pytest

**Agent recommandé**: Agent test/QA  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 QUALITÉ

#### Contexte
Créer une suite de tests d'intégration pour tous les endpoints API.

#### Étapes détaillées

1. **Créer structure de tests**
   ```python
   # tests/api/test_endpoints.py
   import pytest
   from fastapi.testclient import TestClient
   
   def test_health_endpoint(client):
       response = client.get("/api/health")
       assert response.status_code == 200
   ```

2. **Créer tests pour chaque endpoint**
   - `/api/forecasts`
   - `/api/news/feed`
   - `/api/stocks/search`
   - etc.

3. **Exécuter les tests**
   ```bash
   pytest tests/api/
   ```

#### DoD
- [ ] Tests créés pour au moins 10 endpoints
- [ ] Tests passent
- [ ] Coverage > 80% pour les routes
- [ ] CI intégré (si applicable)
- [ ] Preuve: log des tests passants

#### Fichiers à créer
- `tests/api/test_endpoints.py`
- `tests/api/test_forecasts.py`
- `tests/api/test_news.py`
- etc.

---

## 📊 Suivi des Tâches (Mise à jour)

| Tâche | Agent | Status | Points | Date |
|-------|-------|--------|--------|------|
| TASK-QWEN-001 | - | AVAILABLE | +80 | - |
| TASK-QWEN-002 | - | AVAILABLE | +40 | - |
| TASK-QWEN-003 | - | AVAILABLE | +30 | - |
| TASK-QWEN-004 | - | AVAILABLE | +50 | - |
| TASK-QWEN-005 | - | AVAILABLE | +30 | - |
| TASK-QWEN-006 | - | AVAILABLE | +40 | - |
| TASK-QWEN-007 | - | AVAILABLE | +60 | - |
| TASK-QWEN-008 | - | AVAILABLE | +50 | - |
| TASK-QWEN-009 | - | AVAILABLE | +60 | - |
| TASK-QWEN-010 | - | AVAILABLE | +30 | - |
| TASK-QWEN-011 | - | AVAILABLE | +40 | - |
| TASK-QWEN-012 | - | AVAILABLE | +50 | - |
| TASK-QWEN-013 | - | AVAILABLE | +50 | - |
| TASK-QWEN-014 | - | AVAILABLE | +40 | - |
| TASK-QWEN-015 | - | AVAILABLE | +40 | - |
| TASK-QWEN-016 | - | AVAILABLE | +50 | - |
| TASK-QWEN-017 | - | AVAILABLE | +30 | - |
| TASK-QWEN-018 | - | AVAILABLE | +50 | - |
| TASK-QWEN-019 | - | AVAILABLE | +40 | - |
| TASK-QWEN-020 | - | AVAILABLE | +50 | - |
| TASK-QWEN-021 | - | AVAILABLE | +70 | - |
| TASK-QWEN-022 | - | AVAILABLE | +80 | - |
| TASK-QWEN-023 | - | AVAILABLE | +50 | - |
| TASK-QWEN-024 | - | AVAILABLE | +60 | - |
| TASK-QWEN-025 | - | AVAILABLE | +60 | - |
| TASK-QWEN-026 | - | AVAILABLE | +70 | - |
| TASK-QWEN-027 | - | AVAILABLE | +50 | - |
| TASK-QWEN-028 | - | AVAILABLE | +40 | - |
| TASK-QWEN-029 | - | AVAILABLE | +40 | - |
| TASK-QWEN-030 | - | AVAILABLE | +40 | - |
| TASK-QWEN-031 | - | AVAILABLE | +50 | - |
| TASK-QWEN-032 | - | AVAILABLE | +80 | - |
| TASK-QWEN-033 | - | AVAILABLE | +50 | - |
| TASK-QWEN-034 | - | AVAILABLE | +60 | - |
| TASK-QWEN-035 | - | AVAILABLE | +70 | - |

---

## 🔵 PRIORITÉ P3 - Tâches d'Enrichissement

### TASK-QWEN-036 — Améliorer la page Trading avec fonctionnalités complètes

**Agent recommandé**: Agent frontend React  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟢 FEATURE

#### Contexte
La page Trading existe mais peut être enrichie avec plus de fonctionnalités.

#### Étapes détaillées

1. **Lire la page actuelle**
   ```bash
   cat copilot-app/frontend/webapp/src/pages/Trading.tsx
   ```

2. **Ajouter fonctionnalités**
   - Ordre de trading simulé
   - Portfolio virtuel
   - Historique des trades
   - Performance du portfolio

3. **Intégrer avec API backend**
   - Endpoint pour exécuter trades simulés
   - Sauvegarde des trades

#### DoD
- [ ] Page Trading enrichie
- [ ] Ordres simulés fonctionnels
- [ ] Portfolio virtuel affiché
- [ ] Historique des trades visible
- [ ] Preuve: screenshot avec fonctionnalités

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/pages/Trading.tsx`

---

### TASK-QWEN-037 — Créer un widget de corrélation entre actifs

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Un widget affichant la matrice de corrélation entre plusieurs actifs serait utile.

#### Étapes détaillées

1. **Créer composant CorrelationMatrix**
   ```typescript
   // src/components/widgets/CorrelationMatrixWidget.tsx
   import { Heatmap } from '@tremor/react';
   
   export function CorrelationMatrixWidget({ tickers }: { tickers: string[] }) {
     // Fetch données de corrélation
     // Afficher en heatmap
   }
   ```

2. **Intégrer au Dashboard ou page dédiée**
   - Ajouter widget au Dashboard
   - Ou créer page Correlations

3. **Ajouter interactions**
   - Tooltip avec valeur de corrélation
   - Filtre par période

#### DoD
- [ ] Widget CorrelationMatrix créé
- [ ] Heatmap fonctionnel
- [ ] Données de corrélation affichées
- [ ] Interactions (tooltip, filtres) fonctionnelles
- [ ] Preuve: screenshot avec heatmap

#### Fichiers à créer
- `frontend/webapp/src/components/widgets/CorrelationMatrixWidget.tsx`

---

### TASK-QWEN-038 — Implémenter un système de tags/catégories pour les news

**Agent recommandé**: Agent fullstack  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre de tagger et catégoriser les news pour un meilleur filtrage.

#### Étapes détaillées

1. **Backend: Ajouter tags aux news**
   ```python
   # backend/services/news_service.py
   def tag_news(article):
       # Analyser contenu
       # Assigner tags: earnings, merger, regulation, etc.
   ```

2. **Frontend: Afficher tags**
   - Badges de tags sur chaque article
   - Filtre par tag

3. **Backend: Endpoint de filtrage par tag**
   ```python
   @router.get("/news/feed")
   def get_news(tags: Optional[List[str]] = None):
       # Filtrer par tags si fourni
   ```

#### DoD
- [ ] Système de tags implémenté
- [ ] Tags affichés sur les news
- [ ] Filtrage par tag fonctionne
- [ ] Au moins 5 catégories de tags
- [ ] Preuve: screenshot avec tags

#### Fichiers à modifier
- `backend/api/routes/news.py`
- `frontend/webapp/src/components/news/NewsFeed.tsx`

---

### TASK-QWEN-039 — Créer un système de notes/annotations sur les prévisions

**Agent recommandé**: Agent fullstack  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre aux utilisateurs d'ajouter des notes personnelles sur les prévisions.

#### Étapes détaillées

1. **Backend: Endpoints notes**
   ```python
   # backend/api/routes/notes.py
   @router.post("/notes/create")
   def create_note(ticker: str, note: str):
       # Sauvegarder note
   
   @router.get("/notes/{ticker}")
   def get_notes(ticker: str):
       # Retourner notes pour ticker
   ```

2. **Frontend: Composant Notes**
   ```typescript
   // src/components/notes/NotesWidget.tsx
   // Zone de texte pour ajouter note
   // Liste des notes existantes
   ```

3. **Intégrer aux pages**
   - Page Forecasts
   - Page Stocks (détail ticker)

#### DoD
- [ ] Endpoints notes créés
- [ ] Composant Notes créé
- [ ] Ajout/affichage de notes fonctionne
- [ ] Notes persistées
- [ ] Preuve: screenshot avec notes

#### Fichiers à créer
- `backend/api/routes/notes.py`
- `frontend/webapp/src/components/notes/NotesWidget.tsx`

---

### TASK-QWEN-040 — Ajouter un système de partage de rapports

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟢 FEATURE

#### Contexte
Permettre de partager des rapports (briefs, backtests) via lien ou export.

#### Étapes détaillées

1. **Créer composant ShareButton**
   ```typescript
   // src/components/share/ShareButton.tsx
   export function ShareButton({ reportId, type }: { reportId: string, type: 'brief' | 'backtest' }) {
     // Générer lien de partage
     // Copier dans clipboard
     // Ou exporter en PDF
   }
   ```

2. **Ajouter aux pages**
   - Page MarketBrief
   - Page Backtests

3. **Implémenter génération de lien**
   - URL avec paramètres
   - Ou export PDF partageable

#### DoD
- [ ] Composant ShareButton créé
- [ ] Partage fonctionnel (lien ou PDF)
- [ ] Intégré à au moins 2 pages
- [ ] Preuve: screenshot avec bouton de partage

#### Fichiers à créer
- `frontend/webapp/src/components/share/ShareButton.tsx`

---

### TASK-QWEN-041 — Créer un système de filtres sauvegardés

**Agent recommandé**: Agent fullstack  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre de sauvegarder des configurations de filtres pour réutilisation rapide.

#### Étapes détaillées

1. **Backend: Endpoints filtres sauvegardés**
   ```python
   # backend/api/routes/saved_filters.py
   @router.post("/filters/save")
   def save_filter(name: str, filters: dict):
       # Sauvegarder configuration
   
   @router.get("/filters")
   def get_saved_filters():
       # Retourner liste des filtres sauvegardés
   ```

2. **Frontend: UI de gestion**
   - Dropdown avec filtres sauvegardés
   - Bouton "Save current filters"
   - Liste des filtres sauvegardés

3. **Intégrer aux pages**
   - Page Forecasts
   - Page News
   - Page Stocks

#### DoD
- [ ] Endpoints créés
- [ ] UI de gestion fonctionnelle
- [ ] Sauvegarde/chargement fonctionne
- [ ] Intégré à au moins 2 pages
- [ ] Preuve: screenshot avec filtres sauvegardés

#### Fichiers à créer
- `backend/api/routes/saved_filters.py`
- `frontend/webapp/src/components/filters/SavedFilters.tsx`

---

### TASK-QWEN-042 — Ajouter un système de recommandations personnalisées

**Agent recommandé**: Agent backend Python  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 FEATURE

#### Contexte
Générer des recommandations personnalisées basées sur l'historique de l'utilisateur.

#### Étapes détaillées

1. **Créer service de recommandations**
   ```python
   # backend/services/recommendations_service.py
   def generate_recommendations(user_history: dict):
       # Analyser historique (tickers consultés, filtres utilisés)
       # Générer recommandations
       # Retourner liste de tickers/forecasts recommandés
   ```

2. **Créer endpoint**
   ```python
   @router.get("/recommendations")
   def get_recommendations():
       # Retourner recommandations personnalisées
   ```

3. **Frontend: Afficher recommandations**
   - Widget sur Dashboard
   - Section "Pour vous" sur page Forecasts

#### DoD
- [ ] Service de recommandations créé
- [ ] Endpoint fonctionnel
- [ ] Widget d'affichage créé
- [ ] Recommandations pertinentes
- [ ] Preuve: screenshot avec recommandations

#### Fichiers à créer
- `backend/services/recommendations_service.py`
- `frontend/webapp/src/components/recommendations/RecommendationsWidget.tsx`

---

### TASK-QWEN-043 — Créer un système de comparaison de stratégies de trading

**Agent recommandé**: Agent fullstack  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre de comparer plusieurs stratégies de trading côte à côte.

#### Étapes détaillées

1. **Créer page CompareStrategies**
   ```typescript
   // src/pages/CompareStrategies.tsx
   // Sélecteur de 2+ stratégies
   // Tableau comparatif
   // Graphiques côte à côte
   ```

2. **Backend: Endpoint de comparaison**
   ```python
   @router.post("/strategies/compare")
   def compare_strategies(strategies: List[str]):
       # Exécuter backtests pour chaque stratégie
       # Retourner résultats comparés
   ```

3. **Afficher métriques comparées**
   - CAGR, Sharpe, Max Drawdown
   - Graphiques de performance

#### DoD
- [ ] Page CompareStrategies créée
- [ ] Endpoint de comparaison fonctionnel
- [ ] Comparaison de 2+ stratégies fonctionne
- [ ] Métriques comparées affichées
- [ ] Preuve: screenshot avec comparaison

#### Fichiers à créer
- `frontend/webapp/src/pages/CompareStrategies.tsx`
- `backend/api/routes/strategies.py`

---

### TASK-QWEN-044 — Ajouter un système de commentaires sur les prévisions

**Agent recommandé**: Agent fullstack  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟢 FEATURE

#### Contexte
Permettre aux utilisateurs de commenter les prévisions pour discussion.

#### Étapes détaillées

1. **Backend: Endpoints commentaires**
   ```python
   # backend/api/routes/comments.py
   @router.post("/comments/create")
   def create_comment(forecast_id: str, comment: str):
       # Sauvegarder commentaire
   
   @router.get("/comments/{forecast_id}")
   def get_comments(forecast_id: str):
       # Retourner commentaires pour prévision
   ```

2. **Frontend: Composant Comments**
   ```typescript
   // src/components/comments/CommentsSection.tsx
   // Zone de saisie
   // Liste des commentaires
   // Affichage avec timestamps
   ```

3. **Intégrer à ForecastsProBoard**
   - Section commentaires sous chaque prévision

#### DoD
- [ ] Endpoints commentaires créés
- [ ] Composant Comments créé
- [ ] Ajout/affichage fonctionne
- [ ] Intégré à page Forecasts
- [ ] Preuve: screenshot avec commentaires

#### Fichiers à créer
- `backend/api/routes/comments.py`
- `frontend/webapp/src/components/comments/CommentsSection.tsx`

---

### TASK-QWEN-045 — Créer un système de calendrier économique intégré

**Agent recommandé**: Agent fullstack  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Afficher un calendrier des événements économiques à venir (FOMC, NFP, CPI, etc.).

#### Étapes détaillées

1. **Backend: Endpoint calendrier**
   ```python
   # backend/api/routes/calendar.py
   @router.get("/calendar/economic")
   def get_economic_calendar(start_date: str, end_date: str):
       # Récupérer événements économiques
       # Retourner liste structurée
   ```

2. **Frontend: Composant Calendar**
   ```typescript
   // src/components/calendar/EconomicCalendar.tsx
   // Affichage calendrier mensuel
   // Événements marqués
   // Détails au clic
   ```

3. **Intégrer au Dashboard ou page dédiée**
   - Widget sur Dashboard
   - Ou page Calendar complète

#### DoD
- [ ] Endpoint calendrier créé
- [ ] Composant Calendar créé
- [ ] Événements affichés
- [ ] Détails accessibles
- [ ] Preuve: screenshot avec calendrier

#### Fichiers à créer
- `backend/api/routes/calendar.py`
- `frontend/webapp/src/components/calendar/EconomicCalendar.tsx`

---

### TASK-QWEN-046 — Ajouter un système de favoris pour les news

**Agent recommandé**: Agent frontend React  
**Points**: +40 pts  
**Effort estimé**: 2h  
**Priorité**: 🟢 FEATURE

#### Contexte
Permettre de marquer des news comme favorites pour consultation ultérieure.

#### Étapes détaillées

1. **Créer hook useFavorites**
   ```typescript
   // src/hooks/useFavorites.ts
   export function useFavorites() {
     const [favorites, setFavorites] = useState<string[]>([]);
     // Gérer ajout/suppression
   }
   ```

2. **Ajouter bouton favori sur chaque article**
   - Icône étoile
   - Toggle favori

3. **Créer page Favorites**
   - Liste des news favorites
   - Filtres et recherche

#### DoD
- [ ] Hook useFavorites créé
- [ ] Bouton favori fonctionnel
- [ ] Page Favorites créée
- [ ] Favoris persistés (localStorage)
- [ ] Preuve: screenshot avec favoris

#### Fichiers à créer
- `frontend/webapp/src/hooks/useFavorites.ts`
- `frontend/webapp/src/pages/Favorites.tsx`

---

### TASK-QWEN-047 — Créer un système de métriques de performance utilisateur

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 ANALYTICS

#### Contexte
Tracker l'utilisation de l'app pour améliorer l'UX (pages visitées, features utilisées).

#### Étapes détaillées

1. **Créer service d'analytics**
   ```python
   # backend/services/analytics_service.py
   def track_event(event_type: str, data: dict):
       # Logger événement
       # Sauvegarder dans fichier/DB
   ```

2. **Créer endpoints**
   ```python
   @router.post("/analytics/track")
   def track_analytics(event: AnalyticsEvent):
       # Enregistrer événement
   ```

3. **Frontend: Intégrer tracking**
   - Page views
   - Clicks sur boutons
   - Utilisation de features

#### DoD
- [ ] Service d'analytics créé
- [ ] Endpoints créés
- [ ] Tracking intégré frontend
- [ ] Événements enregistrés
- [ ] Preuve: logs d'événements

#### Fichiers à créer
- `backend/services/analytics_service.py`
- `frontend/webapp/src/services/analytics.ts`

---

### TASK-QWEN-048 — Ajouter un système de versioning pour les modèles ML

**Agent recommandé**: Agent backend Python  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 ML OPS

#### Contexte
Tracker les versions des modèles ML et leurs performances.

#### Étapes détaillées

1. **Créer système de versioning**
   ```python
   # backend/models/versioning.py
   class ModelVersion:
       version: str
       created_at: datetime
       performance_metrics: dict
   ```

2. **Créer endpoints**
   ```python
   @router.get("/models/versions")
   def get_model_versions():
       # Retourner liste des versions
   
   @router.get("/models/{version}/performance")
   def get_model_performance(version: str):
       # Retourner métriques de performance
   ```

3. **Frontend: Afficher versions**
   - Page Models avec liste des versions
   - Comparaison de performances

#### DoD
- [ ] Système de versioning créé
- [ ] Endpoints créés
- [ ] UI d'affichage créée
- [ ] Versions trackées
- [ ] Preuve: screenshot avec versions

#### Fichiers à créer
- `backend/models/versioning.py`
- `frontend/webapp/src/pages/Models.tsx`

---

### TASK-QWEN-049 — Créer un système de validation des prévisions (hit rate tracking)

**Agent recommandé**: Agent backend Python  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 ANALYTICS

#### Contexte
Tracker la précision des prévisions en comparant avec les réalisations.

#### Étapes détaillées

1. **Créer service de validation**
   ```python
   # backend/services/forecast_validation.py
   def validate_forecast(forecast_id: str, actual_price: float):
       # Comparer prévision avec réalisation
       # Calculer hit rate
       # Mettre à jour statistiques
   ```

2. **Créer endpoint**
   ```python
   @router.get("/forecasts/validation")
   def get_validation_stats():
       # Retourner hit rate, accuracy, etc.
   ```

3. **Frontend: Afficher statistiques**
   - Widget sur Dashboard
   - Page Validation avec détails

#### DoD
- [ ] Service de validation créé
- [ ] Endpoint créé
- [ ] Hit rate calculé
- [ ] Statistiques affichées
- [ ] Preuve: screenshot avec stats

#### Fichiers à créer
- `backend/services/forecast_validation.py`
- `frontend/webapp/src/components/validation/ValidationStats.tsx`

---

### TASK-QWEN-050 — Ajouter un système de notifications push (browser notifications)

**Agent recommandé**: Agent frontend React  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Envoyer des notifications browser quand des alertes sont déclenchées.

#### Étapes détaillées

1. **Demander permission notifications**
   ```typescript
   // src/services/notifications.ts
   export async function requestNotificationPermission() {
     const permission = await Notification.requestPermission();
   }
   ```

2. **Créer service de notifications**
   ```typescript
   export function sendNotification(title: string, body: string) {
     new Notification(title, { body });
   }
   ```

3. **Intégrer avec alertes**
   - Écouter changements d'alertes
   - Envoyer notification si déclenchée

#### DoD
- [ ] Permission demandée
- [ ] Service de notifications créé
- [ ] Intégré avec alertes
- [ ] Notifications fonctionnelles
- [ ] Preuve: screenshot avec notification

#### Fichiers à créer
- `frontend/webapp/src/services/notifications.ts`

---

## 📊 Suivi des Tâches (Mise à jour finale)

| Tâche | Agent | Status | Points | Date |
|-------|-------|--------|--------|------|
| TASK-QWEN-001 | - | AVAILABLE | +80 | - |
| TASK-QWEN-002 | - | AVAILABLE | +40 | - |
| TASK-QWEN-003 | - | AVAILABLE | +30 | - |
| TASK-QWEN-004 | - | AVAILABLE | +50 | - |
| TASK-QWEN-005 | - | AVAILABLE | +30 | - |
| TASK-QWEN-006 | - | AVAILABLE | +40 | - |
| TASK-QWEN-007 | - | AVAILABLE | +60 | - |
| TASK-QWEN-008 | - | AVAILABLE | +50 | - |
| TASK-QWEN-009 | - | AVAILABLE | +60 | - |
| TASK-QWEN-010 | - | AVAILABLE | +30 | - |
| TASK-QWEN-011 | - | AVAILABLE | +40 | - |
| TASK-QWEN-012 | - | AVAILABLE | +50 | - |
| TASK-QWEN-013 | - | AVAILABLE | +50 | - |
| TASK-QWEN-014 | - | AVAILABLE | +40 | - |
| TASK-QWEN-015 | - | AVAILABLE | +40 | - |
| TASK-QWEN-016 | - | AVAILABLE | +50 | - |
| TASK-QWEN-017 | - | AVAILABLE | +30 | - |
| TASK-QWEN-018 | - | AVAILABLE | +50 | - |
| TASK-QWEN-019 | - | AVAILABLE | +40 | - |
| TASK-QWEN-020 | - | AVAILABLE | +50 | - |
| TASK-QWEN-021 | - | AVAILABLE | +70 | - |
| TASK-QWEN-022 | - | AVAILABLE | +80 | - |
| TASK-QWEN-023 | - | AVAILABLE | +50 | - |
| TASK-QWEN-024 | - | AVAILABLE | +60 | - |
| TASK-QWEN-025 | - | AVAILABLE | +60 | - |
| TASK-QWEN-026 | - | AVAILABLE | +70 | - |
| TASK-QWEN-027 | - | AVAILABLE | +50 | - |
| TASK-QWEN-028 | - | AVAILABLE | +40 | - |
| TASK-QWEN-029 | - | AVAILABLE | +40 | - |
| TASK-QWEN-030 | - | AVAILABLE | +40 | - |
| TASK-QWEN-031 | - | AVAILABLE | +50 | - |
| TASK-QWEN-032 | - | AVAILABLE | +80 | - |
| TASK-QWEN-033 | - | AVAILABLE | +50 | - |
| TASK-QWEN-034 | - | AVAILABLE | +60 | - |
| TASK-QWEN-035 | - | AVAILABLE | +70 | - |
| TASK-QWEN-036 | - | AVAILABLE | +60 | - |
| TASK-QWEN-037 | - | AVAILABLE | +50 | - |
| TASK-QWEN-038 | - | AVAILABLE | +50 | - |
| TASK-QWEN-039 | - | AVAILABLE | +60 | - |
| TASK-QWEN-040 | - | AVAILABLE | +50 | - |
| TASK-QWEN-041 | - | AVAILABLE | +50 | - |
| TASK-QWEN-042 | - | AVAILABLE | +70 | - |
| TASK-QWEN-043 | - | AVAILABLE | +70 | - |
| TASK-QWEN-044 | - | AVAILABLE | +60 | - |
| TASK-QWEN-045 | - | AVAILABLE | +60 | - |
| TASK-QWEN-046 | - | AVAILABLE | +40 | - |
| TASK-QWEN-047 | - | AVAILABLE | +60 | - |
| TASK-QWEN-048 | - | AVAILABLE | +70 | - |
| TASK-QWEN-049 | - | AVAILABLE | +70 | - |
| TASK-QWEN-050 | - | AVAILABLE | +60 | - |

---

## 🟣 PRIORITÉ P4 - Tâches d'Optimisation Avancée

### TASK-QWEN-051 — Améliorer la gestion d'erreurs centralisée dans api/client.ts

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 STABILITÉ

#### Contexte
Le client API doit avoir une gestion d'erreurs robuste et centralisée.

#### Étapes détaillées

1. **Lire le fichier actuel**
   ```bash
   cat copilot-app/frontend/webapp/src/api/client.ts
   ```

2. **Améliorer la gestion d'erreurs**
   ```typescript
   // Ajouter interceptors pour erreurs
   // Gérer codes HTTP spécifiques (401, 403, 500, etc.)
   // Retourner messages d'erreur clairs
   // Logging des erreurs
   ```

3. **Ajouter retry logic**
   - Retry automatique pour erreurs réseau
   - Exponential backoff

#### DoD
- [ ] Gestion d'erreurs centralisée
- [ ] Messages d'erreur clairs pour utilisateur
- [ ] Retry logic implémenté
- [ ] Logging des erreurs
- [ ] Preuve: screenshot avec message d'erreur clair

#### Fichiers à modifier
- `copilot-app/frontend/webapp/src/api/client.ts`

---

### TASK-QWEN-052 — Créer un système de préchargement intelligent (prefetching)

**Agent recommandé**: Agent frontend React  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 PERFORMANCE

#### Contexte
Précharger les données des pages probables pour améliorer la navigation.

#### Étapes détaillées

1. **Créer service de prefetching**
   ```typescript
   // src/services/prefetch.ts
   export function prefetchPageData(route: string) {
     // Précharger données pour route
     // Utiliser React Query prefetchQuery
   }
   ```

2. **Intégrer au router**
   - Précharger données au hover sur liens
   - Ou précharger pages probables

3. **Mesurer amélioration**
   - Temps de chargement avant/après

#### DoD
- [ ] Service de prefetching créé
- [ ] Préchargement au hover fonctionne
- [ ] Performance améliorée (mesurée)
- [ ] Preuve: métriques avant/après

#### Fichiers à créer
- `frontend/webapp/src/services/prefetch.ts`

---

### TASK-QWEN-053 — Ajouter un système de cache local (IndexedDB)

**Agent recommandé**: Agent frontend React  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 PERFORMANCE

#### Contexte
Utiliser IndexedDB pour cache local persistant des données.

#### Étapes détaillées

1. **Installer Dexie.js**
   ```bash
   npm install dexie
   ```

2. **Créer base de données IndexedDB**
   ```typescript
   // src/db/indexedDB.ts
   import Dexie from 'dexie';
   
   class FinanceDB extends Dexie {
     forecasts: Table<Forecast>;
     news: Table<News>;
     // etc.
   }
   ```

3. **Intégrer avec React Query**
   - Utiliser IndexedDB comme cache persistant
   - Synchroniser avec API

#### DoD
- [ ] IndexedDB configuré
- [ ] Cache persistant fonctionnel
- [ ] Synchronisation avec API
- [ ] Données disponibles offline
- [ ] Preuve: screenshot avec données offline

#### Fichiers à créer
- `frontend/webapp/src/db/indexedDB.ts`

---

### TASK-QWEN-054 — Créer un système de monitoring des erreurs (Sentry-like)

**Agent recommandé**: Agent fullstack  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 OBSERVABILITÉ

#### Contexte
Tracker les erreurs en production pour debugging.

#### Étapes détaillées

1. **Backend: Service de logging d'erreurs**
   ```python
   # backend/services/error_tracking.py
   def log_error(error: Exception, context: dict):
       # Logger erreur avec contexte
       # Sauvegarder dans fichier/DB
   ```

2. **Frontend: Error boundary avec reporting**
   ```typescript
   // Capturer erreurs React
   // Envoyer au backend
   ```

3. **Dashboard d'erreurs**
   - Page Admin avec liste des erreurs
   - Statistiques d'erreurs

#### DoD
- [ ] Service de tracking créé
- [ ] Erreurs capturées et loggées
- [ ] Dashboard d'erreurs créé
- [ ] Statistiques affichées
- [ ] Preuve: screenshot avec erreurs trackées

#### Fichiers à créer
- `backend/services/error_tracking.py`
- `frontend/webapp/src/pages/Admin/Errors.tsx`

---

### TASK-QWEN-055 — Ajouter un système de A/B testing pour les features

**Agent recommandé**: Agent fullstack  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 ANALYTICS

#### Contexte
Permettre de tester différentes versions de features.

#### Étapes détaillées

1. **Créer service A/B testing**
   ```python
   # backend/services/ab_testing.py
   def assign_variant(user_id: str, test_name: str):
       # Assigner variant A ou B
       # Sauvegarder assignation
   ```

2. **Frontend: Utiliser variants**
   ```typescript
   // Afficher variant A ou B selon assignation
   // Tracker conversions
   ```

3. **Dashboard de résultats**
   - Afficher statistiques A/B
   - Déterminer variant gagnant

#### DoD
- [ ] Service A/B testing créé
- [ ] Variants assignés
- [ ] Conversions trackées
- [ ] Dashboard de résultats créé
- [ ] Preuve: screenshot avec résultats A/B

#### Fichiers à créer
- `backend/services/ab_testing.py`
- `frontend/webapp/src/services/abTesting.ts`

---

### TASK-QWEN-056 — Créer un système de migration de données (schema versioning)

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 MAINTENANCE

#### Contexte
Gérer les migrations de schéma de données lors des mises à jour.

#### Étapes détaillées

1. **Créer système de migrations**
   ```python
   # backend/migrations/001_initial_schema.py
   def up():
       # Créer structure initiale
   
   def down():
       # Rollback
   ```

2. **Créer script de migration**
   ```bash
   # scripts/migrate.py
   # Appliquer migrations dans l'ordre
   ```

3. **Intégrer au démarrage**
   - Vérifier version actuelle
   - Appliquer migrations nécessaires

#### DoD
- [ ] Système de migrations créé
- [ ] Au moins 2 migrations d'exemple
- [ ] Script de migration fonctionnel
- [ ] Migrations appliquées au démarrage
- [ ] Preuve: log de migration appliquée

#### Fichiers à créer
- `backend/migrations/` (dossier)
- `backend/scripts/migrate.py`

---

### TASK-QWEN-057 — Ajouter un système de quotas et limites utilisateur

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 SÉCURITÉ

#### Contexte
Limiter l'utilisation des ressources par utilisateur.

#### Étapes détaillées

1. **Créer service de quotas**
   ```python
   # backend/services/quota_service.py
   def check_quota(user_id: str, resource: str):
       # Vérifier si quota disponible
       # Retourner True/False
   ```

2. **Intégrer aux endpoints**
   - Vérifier quota avant traitement
   - Retourner 429 si quota dépassé

3. **Frontend: Afficher quotas**
   - Widget avec utilisation actuelle
   - Barre de progression

#### DoD
- [ ] Service de quotas créé
- [ ] Quotas appliqués aux endpoints
- [ ] UI d'affichage créée
- [ ] Limites respectées
- [ ] Preuve: screenshot avec quotas affichés

#### Fichiers à créer
- `backend/services/quota_service.py`
- `frontend/webapp/src/components/quota/QuotaWidget.tsx`

---

### TASK-QWEN-058 — Créer un système de templates de rapports personnalisables

**Agent recommandé**: Agent fullstack  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre de créer des templates de rapports personnalisés.

#### Étapes détaillées

1. **Backend: Endpoints templates**
   ```python
   # backend/api/routes/templates.py
   @router.post("/templates/create")
   def create_template(template: ReportTemplate):
       # Sauvegarder template
   
   @router.get("/templates")
   def get_templates():
       # Retourner templates disponibles
   ```

2. **Frontend: Éditeur de templates**
   - Interface drag-and-drop
   - Sélection de widgets/métriques
   - Prévisualisation

3. **Génération de rapports**
   - Utiliser template pour générer rapport
   - Export PDF/HTML

#### DoD
- [ ] Endpoints templates créés
- [ ] Éditeur de templates créé
- [ ] Création de template fonctionne
- [ ] Génération de rapport avec template fonctionne
- [ ] Preuve: screenshot avec template créé

#### Fichiers à créer
- `backend/api/routes/templates.py`
- `frontend/webapp/src/components/templates/TemplateEditor.tsx`

---

### TASK-QWEN-059 — Ajouter un système de collaboration (partage de dashboards)

**Agent recommandé**: Agent fullstack  
**Points**: +80 pts  
**Effort estimé**: 5h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre de partager des dashboards avec d'autres utilisateurs.

#### Étapes détaillées

1. **Backend: Endpoints partage**
   ```python
   # backend/api/routes/sharing.py
   @router.post("/dashboards/{id}/share")
   def share_dashboard(dashboard_id: str, users: List[str]):
       # Partager dashboard avec utilisateurs
   
   @router.get("/dashboards/shared")
   def get_shared_dashboards():
       # Retourner dashboards partagés
   ```

2. **Frontend: UI de partage**
   - Modal de partage
   - Liste des utilisateurs
   - Permissions (read/write)

3. **Afficher dashboards partagés**
   - Section "Shared with me"
   - Badge "Shared" sur dashboards

#### DoD
- [ ] Endpoints partage créés
- [ ] UI de partage fonctionnelle
- [ ] Partage fonctionne
- [ ] Dashboards partagés affichés
- [ ] Preuve: screenshot avec dashboard partagé

#### Fichiers à créer
- `backend/api/routes/sharing.py`
- `frontend/webapp/src/components/sharing/ShareModal.tsx`

---

### TASK-QWEN-060 — Créer un système de webhooks pour intégrations externes

**Agent recommandé**: Agent backend Python  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 INTÉGRATION

#### Contexte
Permettre à des systèmes externes de recevoir des notifications.

#### Étapes détaillées

1. **Créer service de webhooks**
   ```python
   # backend/services/webhook_service.py
   def register_webhook(url: str, events: List[str]):
       # Enregistrer webhook
   
   def trigger_webhook(event: str, data: dict):
       # Déclencher webhook
   ```

2. **Créer endpoints**
   ```python
   @router.post("/webhooks/register")
   def register_webhook(webhook: WebhookConfig):
       # Enregistrer webhook
   ```

3. **Intégrer aux événements**
   - Déclencher webhook sur alertes
   - Déclencher sur nouvelles prévisions

#### DoD
- [ ] Service de webhooks créé
- [ ] Endpoints créés
- [ ] Enregistrement fonctionne
- [ ] Déclenchement fonctionne
- [ ] Preuve: log de webhook déclenché

#### Fichiers à créer
- `backend/services/webhook_service.py`
- `backend/api/routes/webhooks.py`

---

### TASK-QWEN-061 — Ajouter un système de recherche avancée avec filtres complexes

**Agent recommandé**: Agent fullstack  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 FEATURE

#### Contexte
Permettre des recherches complexes avec plusieurs critères.

#### Étapes détaillées

1. **Backend: Endpoint recherche avancée**
   ```python
   @router.post("/search/advanced")
   def advanced_search(query: AdvancedSearchQuery):
       # Recherche avec filtres multiples
       # Retourner résultats
   ```

2. **Frontend: Interface de recherche**
   - Formulaire avec plusieurs champs
   - Opérateurs logiques (AND, OR)
   - Prévisualisation des résultats

3. **Sauvegarder recherches**
   - Bouton "Save search"
   - Réutiliser recherches sauvegardées

#### DoD
- [ ] Endpoint recherche avancée créé
- [ ] Interface de recherche créée
- [ ] Recherche avec filtres multiples fonctionne
- [ ] Sauvegarde de recherche fonctionne
- [ ] Preuve: screenshot avec recherche avancée

#### Fichiers à créer
- `backend/api/routes/search_advanced.py`
- `frontend/webapp/src/components/search/AdvancedSearch.tsx`

---

### TASK-QWEN-062 — Créer un système de génération automatique de rapports périodiques

**Agent recommandé**: Agent backend Python  
**Points**: +70 pts  
**Effort estimé**: 4h  
**Priorité**: 🟡 FEATURE

#### Contexte
Générer automatiquement des rapports quotidiens/hebdomadaires.

#### Étapes détaillées

1. **Créer service de génération**
   ```python
   # backend/services/report_generator.py
   def generate_daily_report():
       # Générer rapport quotidien
       # Inclure: KPIs, top signaux, risques
   ```

2. **Intégrer au scheduler**
   ```python
   # Générer rapport quotidien à 8h
   scheduler.add_job(generate_daily_report, "cron", hour=8)
   ```

3. **Frontend: Afficher rapports générés**
   - Page Reports avec historique
   - Téléchargement PDF

#### DoD
- [ ] Service de génération créé
- [ ] Génération automatique configurée
- [ ] Rapports générés et sauvegardés
- [ ] UI d'affichage créée
- [ ] Preuve: rapport généré

#### Fichiers à créer
- `backend/services/report_generator.py`
- `frontend/webapp/src/pages/Reports.tsx`

---

### TASK-QWEN-063 — Ajouter un système de validation de données en temps réel

**Agent recommandé**: Agent backend Python  
**Points**: +50 pts  
**Effort estimé**: 2-3h  
**Priorité**: 🟡 QUALITÉ

#### Contexte
Valider la qualité des données en temps réel et alerter si anomalies.

#### Étapes détaillées

1. **Créer service de validation**
   ```python
   # backend/services/data_validation.py
   def validate_data_quality(data: dict):
       # Vérifier cohérence
       # Détecter anomalies
       # Retourner rapport de validation
   ```

2. **Intégrer aux pipelines**
   - Valider après ingestion
   - Alerter si problèmes détectés

3. **Frontend: Afficher statut validation**
   - Badge de qualité des données
   - Détails des validations

#### DoD
- [ ] Service de validation créé
- [ ] Validation intégrée aux pipelines
- [ ] Alertes fonctionnelles
- [ ] UI d'affichage créée
- [ ] Preuve: screenshot avec validation

#### Fichiers à créer
- `backend/services/data_validation.py`
- `frontend/webapp/src/components/validation/DataQualityBadge.tsx`

---

### TASK-QWEN-064 — Créer un système de gestion de versions pour les configurations

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 MAINTENANCE

#### Contexte
Tracker les changements de configuration pour rollback si nécessaire.

#### Étapes détaillées

1. **Créer système de versioning**
   ```python
   # backend/services/config_versioning.py
   def save_config_version(config: dict):
       # Sauvegarder version avec timestamp
   
   def get_config_history():
       # Retourner historique
   ```

2. **Créer endpoints**
   ```python
   @router.get("/config/history")
   def get_config_history():
       # Retourner historique
   
   @router.post("/config/rollback")
   def rollback_config(version: str):
       # Restaurer version précédente
   ```

3. **Frontend: UI de gestion**
   - Historique des configurations
   - Bouton de rollback

#### DoD
- [ ] Système de versioning créé
- [ ] Endpoints créés
- [ ] Historique tracké
- [ ] Rollback fonctionnel
- [ ] Preuve: screenshot avec historique

#### Fichiers à créer
- `backend/services/config_versioning.py`
- `frontend/webapp/src/pages/Admin/ConfigHistory.tsx`

---

### TASK-QWEN-065 — Ajouter un système de métriques business (KPIs métier)

**Agent recommandé**: Agent backend Python  
**Points**: +60 pts  
**Effort estimé**: 3h  
**Priorité**: 🟡 ANALYTICS

#### Contexte
Tracker des métriques business (nombre d'utilisateurs, prévisions générées, etc.).

#### Étapes détaillées

1. **Créer service de métriques business**
   ```python
   # backend/services/business_metrics.py
   def calculate_business_kpis():
       # Calculer KPIs métier
       # Retourner métriques
   ```

2. **Créer endpoint**
   ```python
   @router.get("/analytics/business")
   def get_business_metrics():
       # Retourner KPIs métier
   ```

3. **Frontend: Dashboard business**
   - Page Analytics avec KPIs
   - Graphiques d'évolution

#### DoD
- [ ] Service de métriques créé
- [ ] Endpoint créé
- [ ] KPIs calculés
- [ ] Dashboard business créé
- [ ] Preuve: screenshot avec KPIs

#### Fichiers à créer
- `backend/services/business_metrics.py`
- `frontend/webapp/src/pages/Analytics/Business.tsx`

---

## 📊 Suivi des Tâches (Mise à jour finale complète)

| Tâche | Agent | Status | Points | Date |
|-------|-------|--------|--------|------|
| TASK-QWEN-001 à 050 | - | AVAILABLE | +2,800 | - |
| TASK-QWEN-051 | - | AVAILABLE | +50 | - |
| TASK-QWEN-052 | - | AVAILABLE | +50 | - |
| TASK-QWEN-053 | - | AVAILABLE | +60 | - |
| TASK-QWEN-054 | - | AVAILABLE | +70 | - |
| TASK-QWEN-055 | - | AVAILABLE | +70 | - |
| TASK-QWEN-056 | - | AVAILABLE | +60 | - |
| TASK-QWEN-057 | - | AVAILABLE | +60 | - |
| TASK-QWEN-058 | - | AVAILABLE | +70 | - |
| TASK-QWEN-059 | - | AVAILABLE | +80 | - |
| TASK-QWEN-060 | - | AVAILABLE | +70 | - |
| TASK-QWEN-061 | - | AVAILABLE | +60 | - |
| TASK-QWEN-062 | - | AVAILABLE | +70 | - |
| TASK-QWEN-063 | - | AVAILABLE | +50 | - |
| TASK-QWEN-064 | - | AVAILABLE | +60 | - |
| TASK-QWEN-065 | - | AVAILABLE | +60 | - |

**Total points disponibles**: **+3,500 pts** 🎯

**Total tâches**: **65 tâches détaillées** 🚀

---

## ✅ Checklist pour Chaque Agent

Avant de commencer:
- [ ] Lu `AGENTS.md`
- [ ] Lu `AGENTS_GAMEPLAY.md`
- [ ] Vérifié qu'aucun autre agent ne travaille sur la tâche
- [ ] Créé fichier de tracking personnel
- [ ] Testé `./finance-copilot.sh start` localement

Pendant le travail:
- [ ] Suivi les étapes détaillées
- [ ] Testé régulièrement
- [ ] Respecté les patterns (never-empty, lazy loading, etc.)

Après complétion:
- [ ] Tous les DoD vérifiés
- [ ] Preuve créée (screenshot/log)
- [ ] Commit avec nom et points
- [ ] `SCORE_AGENTS.md` mis à jour
- [ ] Tâche marquée comme "DONE" dans ce fichier

---

**Bonne chance, agents !** 🚀

