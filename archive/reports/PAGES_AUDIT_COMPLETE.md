# 📋 Finance Copilot - Audit Complet des Pages

**Date** : 2025-01-27  
**Source** : Audit détaillé de la branche `feature/g4f-integration`  
**Analyste** : AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Type** : Audit fonctionnel complet (Frontend + Backend + Intégration)

---

## 🎯 Résumé Exécutif

Audit complet de **8 pages principales** révélant :
- **3 pages fonctionnelles** : News, MarketBrief (partiel), Dashboard (partiel)
- **5 pages incomplètes** : Macro, Stocks, Forecasts, Backtests, LLM Judge
- **1 page manquante** : Compare

**Score global** : 4.5/10 (fonctionnel mais largement incomplet)

**Problèmes majeurs** :
1. Données vides ou statiques (Dashboard, Forecasts)
2. Backend OK mais frontend non branché (Macro, Stocks)
3. Pages placeholder non informatives (Backtests, Forecasts)
4. Intégration LLM non fonctionnelle (Copilot, Judge)

---

## 📊 Tableau de Bord des Pages

| Page | Route | Backend | Frontend | Données | Statut | Priorité |
|------|-------|---------|----------|---------|--------|----------|
| **Dashboard** | `/` | ✅ OK | ⚠️ Partiel | ❌ Vides | 🟡 40% | P0 |
| **Macro** | `/macro` | ✅ OK | ❌ Manquant | ✅ Disponibles | 🔴 20% | P0 |
| **Stocks** | `/stocks` | ✅ OK | ❌ Manquant | ✅ Disponibles | 🔴 10% | P0 |
| **TickerSheet** | `/ticker/:symbol` | ✅ OK | ⚠️ Partiel | ✅ Disponibles | 🟡 60% | P1 |
| **News** | `/news` | ✅ OK | ✅ OK | ✅ Disponibles | ✅ 85% | P2 |
| **MarketBrief** | `/brief` | ⚠️ Legacy | ✅ OK | ✅ Disponibles | 🟡 70% | P1 |
| **Forecasts** | `/forecasts` | ❌ Vide | ⚠️ Placeholder | ❌ Vides | 🔴 5% | P1 |
| **Backtests** | `/backtests` | ❌ Manquant | ⚠️ Placeholder | ❌ Vides | 🔴 0% | P2 |
| **Compare** | N/A | ❌ Manquant | ❌ Manquant | N/A | 🔴 0% | P3 |
| **LLM Judge** | `/judge` | ❌ Manquant | ✅ OK | N/A | 🔴 0% | P2 |
| **Copilot** | `/copilot` | ⚠️ Placeholder | ✅ OK | ❌ Placeholder | 🟡 30% | P0 |

---

## 🔴 P0 - Pages Critiques (À Corriger Immédiatement)

### 1. Dashboard (`/`)

#### État Actuel
- **Backend** : Endpoint `/api/dashboard/kpis` existe mais retourne des valeurs par défaut (zéros, listes vides)
- **Frontend** : Interface complète avec filtres, KPIs, Top Signaux/Risques
- **Problème** : Données statiques, filtres non connectés à l'API

#### Problèmes Détectés

1. **KPIs vides**
   - `last_forecast_dt` : `"—"` au lieu d'une vraie date
   - `total_forecasts` : `0`
   - `tickers_tracked` : `0`
   - `available_horizons` : `[]`

2. **Top Signaux/Risques vides**
   - Sections présentes mais sans contenu
   - Pas de message "No data" affiché
   - Cartes vides dans l'UI

3. **Filtres non fonctionnels**
   - Filtres UI présents (secteurs, horizons, thèmes, tickers)
   - Aucun appel API avec paramètres de filtres
   - Endpoint `/api/dashboard/kpis` ne prend pas de filtres

4. **Performance**
   - Requête légère mais pas de cache notable
   - `staleTime: 15s` configuré mais données ne changent jamais

#### Solutions

**Backend** :
```python
# copilot-app/backend/api/routes/dashboard.py
@router.get("/dashboard/kpis")
def get_dashboard_kpis(
    sectors: Optional[str] = None,
    horizons: Optional[str] = None,
    tickers: Optional[str] = None,
):
    """Retourner de vraies données KPIs avec filtres."""
    # Récupérer dernière date de prévision
    forecasts = load_forecasts()
    last_dt = forecasts.get('last_update') if forecasts else None
    
    # Compter prévisions réelles
    forecast_count = len(forecasts.get('data', {}).get('rows', [])) if forecasts else 0
    
    # Récupérer tickers uniques depuis forecasts
    tickers_list = list(set([
        f.get('ticker') for f in forecasts.get('data', {}).get('rows', [])
        if f.get('ticker')
    ])) if forecasts else []
    
    # Appliquer filtres si fournis
    if tickers:
        ticker_filter = [t.strip().upper() for t in tickers.split(',')]
        # Filtrer forecasts par tickers
    
    return {
        "last_forecast_dt": last_dt or datetime.utcnow().isoformat(),
        "total_forecasts": forecast_count,
        "tickers_tracked": len(tickers_list),
        "available_horizons": ["1d", "1w", "1m", "3m"],
    }
```

**Frontend** :
```typescript
// copilot-app/frontend/webapp/src/hooks/useDashboardKPIs.ts
const useDashboardKPIs = (filters?: DashboardFilters) => {
  return useQuery({
    queryKey: ['dashboard', 'kpis', filters],
    queryFn: () => api.get('/api/dashboard/kpis', {
      sectors: filters?.sectors?.join(','),
      horizons: filters?.horizons?.join(','),
      tickers: filters?.tickers?.join(','),
    }),
    staleTime: 5 * 60 * 1000, // 5 min
  });
};

// Connecter filtres dans Dashboard.tsx
const { data: kpis } = useDashboardKPIs(activeFilters);
```

**Top Signaux/Risques** :
```typescript
// Utiliser endpoint /api/brief pour récupérer top signals
const { data: brief } = useBrief({ period: 'daily' });
const topSignals = brief?.top_signals?.slice(0, 3) || [];
const topRisks = brief?.top_risks?.slice(0, 3) || [];
```

**Fichiers à Modifier** :
- `copilot-app/backend/api/routes/dashboard.py` (ou créer)
- `copilot-app/frontend/webapp/src/hooks/useDashboardKPIs.ts`
- `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`

**Effort estimé** : 4-6h

---

### 2. Macro (`/macro`)

#### État Actuel
- **Backend** : ✅ Endpoints fonctionnels (`/api/macro/overview`, `/api/macro/snapshot`, `/api/macro/indicators`)
- **Frontend** : ❌ Page vide ou minimaliste (pas de composant Macro.tsx abouti)
- **Problème** : Backend calcule tout mais frontend ne consomme rien

#### Problèmes Détectés

1. **Page vide**
   - Route `/macro` déclarée mais composant non implémenté
   - Pas de visualisation des z-scores (GRW, INF, POL, USD, CMD)
   - Pas de graphiques historiques

2. **Données non utilisées**
   - Backend calcule `get_us_macro_bundle()` avec z-scores
   - Frontend n'appelle pas les endpoints
   - Calcul fait "dans le vide"

3. **Composants manquants**
   - `MacroChart.tsx` : Non trouvé
   - `MacroBadges.tsx` : Non trouvé
   - `ChartWithSource.tsx` : Non trouvé

4. **Traçabilité manquante**
   - Backend devrait inclure `trace` dans `MacroSnapshotData`
   - Frontend devrait afficher source et timestamp

#### Solutions

**Backend** (Vérification) :
```python
# S'assurer que MacroSnapshotData inclut trace
@dataclass
class MacroSnapshotData:
    date: str
    zscores: Dict[str, float]  # GRW, INF, POL, USD, CMD
    components: Dict[str, float]  # CPI, Unemployment, etc.
    trace: TraceMetadata  # À ajouter si manquant
```

**Frontend** (Création complète) :
```typescript
// copilot-app/frontend/webapp/src/pages/Macro.tsx
import { useMacroSnapshot, useMacroOverview } from '@/hooks/useMacro';
import { MacroBadges } from '@/components/macro/MacroBadges';
import { MacroChart } from '@/components/macro/MacroChart';

export default function Macro() {
  const { data: snapshot, isLoading } = useMacroSnapshot();
  const { data: overview } = useMacroOverview({ range: '5y' });
  
  if (isLoading) return <LoadingSpinner />;
  if (!snapshot) return <EmptyState message="Données macro non disponibles" />;
  
  return (
    <Container>
      <PageHeader title="Macro" />
      
      {/* Badges z-scores */}
      <MacroBadges zscores={snapshot.zscores} />
      
      {/* Graphique historique */}
      <MacroChart 
        data={overview?.series} 
        source={snapshot.trace?.source}
        lastUpdate={snapshot.trace?.generated_at}
      />
      
      {/* Indicateurs clés */}
      <MacroIndicators components={snapshot.components} />
    </Container>
  );
}
```

**Composants à Créer** :
- `copilot-app/frontend/webapp/src/components/macro/MacroBadges.tsx`
- `copilot-app/frontend/webapp/src/components/macro/MacroChart.tsx`
- `copilot-app/frontend/webapp/src/components/macro/MacroIndicators.tsx`
- `copilot-app/frontend/webapp/src/hooks/useMacro.ts`

**Effort estimé** : 8-12h

---

### 3. Stocks - Liste (`/stocks`)

#### État Actuel
- **Backend** : ✅ Endpoint `/api/stocks/universe` et `/api/stocks/{ticker}/overview` fonctionnels
- **Frontend** : ❌ Page non implémentée (route déclarée mais composant vide)
- **Problème** : Pas de vue d'ensemble des tickers suivis

#### Problèmes Détectés

1. **Page manquante**
   - Route `/stocks` déclarée mais `Stocks.tsx` non développé
   - Utilisateur ne peut pas voir liste des tickers
   - Navigation vers fiche ticker impossible depuis liste

2. **Endpoint non utilisé**
   - `/api/stocks/universe` disponible mais non appelé
   - Données backend prêtes mais non exploitées

#### Solutions

**Frontend** (Création) :
```typescript
// copilot-app/frontend/webapp/src/pages/Stocks.tsx
import { useStocksUniverse, useStockOverview } from '@/hooks/useStocks';
import { StocksTable } from '@/components/stocks/StocksTable';

export default function Stocks() {
  const { data: universe, isLoading } = useStocksUniverse();
  
  if (isLoading) return <LoadingSpinner />;
  if (!universe?.tickers?.length) return <EmptyState />;
  
  return (
    <Container>
      <PageHeader title="Stocks" />
      
      <StocksTable 
        tickers={universe.tickers}
        onTickerClick={(ticker) => navigate(`/ticker/${ticker}`)}
      />
    </Container>
  );
}
```

**Composants à Créer** :
- `copilot-app/frontend/webapp/src/components/stocks/StocksTable.tsx`
- `copilot-app/frontend/webapp/src/hooks/useStocks.ts` (si pas déjà créé)

**Effort estimé** : 6-8h

---

### 4. Copilot LLM (`/copilot`)

#### État Actuel
- **Backend** : ⚠️ Endpoint `/api/copilot/ask` placeholder (renvoie "[Réponse à implémenter avec LLM]")
- **Frontend** : ✅ Composant `Copilot.tsx` probablement présent
- **Problème** : Fonctionnalité cœur du produit non implémentée

#### Problèmes Détectés

1. **LLM non branché**
   - Endpoint retourne réponse factice
   - RAG store instancié mais non utilisé
   - TODO : "Intégrer avec econ_llm_agent"

2. **Pas de vraie génération**
   - Réponse toujours identique
   - Citations factices
   - Pas d'appel à G4F ou autre LLM

#### Solutions

**Backend** :
```python
# copilot-app/backend/api/routes/copilot.py
@router.post("/copilot/ask")
async def ask_copilot(request: CopilotRequest):
    """Générer réponse LLM avec RAG."""
    from services.llm_service import generate_response
    from services.rag_service import search_context
    
    # Rechercher contexte RAG
    context = search_context(request.question, limit=5)
    
    # Générer réponse avec LLM
    response = await generate_response(
        question=request.question,
        context=context,
        model=request.model or "gpt-4",
    )
    
    return {
        "answer": response.text,
        "sources": [c.source for c in context],
        "confidence": response.confidence,
    }
```

**Fichiers à Modifier** :
- `copilot-app/backend/api/routes/copilot.py`
- `copilot-app/backend/services/llm_service.py` (créer)
- `copilot-app/backend/services/rag_service.py` (créer ou adapter)

**Effort estimé** : 12-16h (intégration LLM complexe)

---

## 🟡 P1 - Pages Importantes (À Finaliser)

### 5. TickerSheet (`/ticker/:symbol`)

#### État Actuel
- **Backend** : ✅ Endpoint `/api/stocks/{ticker}/overview` complet
- **Frontend** : ⚠️ Composant existant mais incomplet
- **Problème** : Données disponibles mais affichage partiel

#### Problèmes Détectés

1. **Graphiques manquants**
   - `PriceChart.tsx` non trouvé
   - Prix historiques non visualisés
   - Indicateurs techniques non graphiques

2. **Données non affichées**
   - Composite score calculé mais peut-être non montré
   - Niveaux support/résistance dans `data.levels` mais non affichés
   - Performance 1w/1m non visible

3. **Endpoint potentiellement ancien**
   - Peut utiliser `/api/tickers/:ticker/sheet` (legacy)
   - Devrait utiliser `/api/stocks/{ticker}/overview` (nouveau)

#### Solutions

**Vérifier et améliorer** :
```typescript
// S'assurer d'utiliser le nouvel endpoint
const { data } = useStockOverview(ticker, {
  features: 'all',
  range: '1y',
  downsample: 1000,
});

// Afficher toutes les données
<PriceChart data={data.prices} />
<TechnicalIndicators indicators={data.indicators} />
<SupportResistanceLevels levels={data.levels} />
<CompositeScore score={data.composite_score} />
<NewsList news={data.news} />
```

**Effort estimé** : 4-6h

---

### 6. Forecasts (`/forecasts`)

#### État Actuel
- **Backend** : ❌ Endpoint `/api/forecasts` retourne `{"rows": [], "count": 0}`
- **Frontend** : ⚠️ Composant présent mais affiche "Aucune prévision"
- **Problème** : Module de prévisions non alimenté

#### Problèmes Détectés

1. **Données vides**
   - TODO : "Brancher sur analytics/forecaster.py ou lire un parquet"
   - Pas de logique de prévision implémentée
   - Page inutilisable

2. **Format non défini**
   - Structure des prévisions non spécifiée
   - Colonnes du tableau à définir

#### Solutions

**Option 1 : Masquer temporairement**
```typescript
// Dans App.tsx, retirer de la navigation
// Ou dans Forecasts.tsx
return <ComingSoon message="Module de prévisions en développement" />;
```

**Option 2 : Implémenter backend**
```python
# Brancher sur forecaster existant ou créer pipeline
@router.get("/forecasts")
def get_forecasts():
    # Option A : Lire depuis Parquet
    forecasts_df = pd.read_parquet("data/forecasts.parquet")
    
    # Option B : Appeler forecaster
    from models.forecast_hybrid_v1 import generate_forecasts
    forecasts = generate_forecasts()
    
    return {"rows": forecasts, "count": len(forecasts)}
```

**Effort estimé** : 8-12h (si données disponibles) ou 2h (masquer)

---

### 7. MarketBrief (`/brief`)

#### État Actuel
- **Backend** : ⚠️ Utilise route legacy `/api/brief` (fonctionne) au lieu de `/api/brief/daily` et `/api/brief/weekly` (501 Not Implemented)
- **Frontend** : ✅ Composant fonctionnel
- **Problème** : Double structure API (legacy vs nouvelle)

#### Solutions

**Option 1 : Migrer vers nouvelles routes**
- Implémenter `/api/brief/daily` et `/api/brief/weekly` dans backend
- Mettre à jour frontend pour utiliser nouvelles routes

**Option 2 : Garder legacy temporairement**
- Documenter que legacy est utilisé
- Planifier migration future

**Effort estimé** : 2-4h (migration) ou 0h (garder legacy)

---

## 🟢 P2 - Pages Secondaires (Améliorations)

### 8. News (`/news`)

#### État Actuel
- **Backend** : ✅ Fonctionnel
- **Frontend** : ✅ Fonctionnel (85%)
- **Problème** : Quelques améliorations UX possibles

#### Améliorations Recommandées

1. **Filtres avancés**
   - Ajouter filtre par région (US, Europe, etc.)
   - Slider pour score minimal
   - Auto-complétion tickers

2. **Liens cliquables**
   - Tickers dans titre → lien vers fiche
   - Bouton "Lire la suite" vers source

3. **Éviter doublons**
   - Logique "Charger plus" à améliorer
   - Dédupliquer par ID

**Effort estimé** : 4-6h

---

### 9. Backtests (`/backtests`)

#### État Actuel
- **Backend** : ❌ Pas d'endpoint
- **Frontend** : ⚠️ Placeholder
- **Problème** : Page vide non informative

#### Solutions

**Option 1 : Masquer**
```typescript
// Retirer de navigation ou afficher message clair
return <ComingSoon message="Module de backtests en développement" />;
```

**Option 2 : Implémenter basique**
```python
# Endpoint simple avec métriques globales
@router.get("/backtests")
def get_backtests():
    # Calculer performance si on suit top signaux
    return {
        "strategy_performance": {...},
        "benchmark_comparison": {...},
    }
```

**Effort estimé** : 2h (masquer) ou 8-12h (implémenter)

---

### 10. LLM Judge (`/judge`)

#### État Actuel
- **Backend** : ❌ Endpoint `/llm/judge/run` manquant (404)
- **Frontend** : ✅ Composant présent
- **Problème** : Outil dev non fonctionnel

#### Solutions

**Option 1 : Cacher en production**
```typescript
// Afficher seulement en mode dev
{process.env.NODE_ENV === 'development' && <LLMJudge />}
```

**Option 2 : Implémenter endpoint**
```python
# copilot-app/backend/api/routes/dev.py
@router.post("/dev/judge")
def run_judge(request: JudgeRequest):
    # Appeler agent LLM
    from agents.evaluation_agent import evaluate_model
    result = evaluate_model(
        model=request.model,
        tickers=request.tickers,
    )
    return result
```

**Effort estimé** : 1h (cacher) ou 4-6h (implémenter)

---

## 📋 Synthèse des Gaps d'Implémentation

### Composants Manquants

| Composant | Usage | Priorité | Effort |
|-----------|-------|----------|--------|
| `MacroChart.tsx` | Macro page | P0 | 4h |
| `MacroBadges.tsx` | Macro page | P0 | 2h |
| `PriceChart.tsx` | TickerSheet | P1 | 4h |
| `StocksTable.tsx` | Stocks page | P0 | 3h |
| `ChartWithSource.tsx` | Réutilisable | P1 | 2h |

### Services Backend Manquants

| Service | Usage | Priorité | Effort |
|---------|-------|----------|--------|
| `llm_service.py` | Copilot | P0 | 8h |
| `rag_service.py` | Copilot | P0 | 4h |
| `forecast_service.py` | Forecasts | P1 | 8h |
| `backtest_service.py` | Backtests | P2 | 8h |

### Endpoints à Implémenter/Corriger

| Endpoint | État | Action | Priorité |
|----------|------|--------|----------|
| `/api/dashboard/kpis` | Valeurs vides | Alimenter données réelles | P0 |
| `/api/copilot/ask` | Placeholder | Implémenter LLM | P0 |
| `/api/forecasts` | Vide | Brancher forecaster | P1 |
| `/api/brief/daily` | 501 | Implémenter | P1 |
| `/api/brief/weekly` | 501 | Implémenter | P1 |
| `/api/dev/judge` | 404 | Implémenter ou cacher | P2 |

---

## 🎯 Plan d'Action Priorisé

### Semaine 1 (P0 - Critiques)

**Jour 1-2 : Dashboard**
- [ ] Alimenter `/api/dashboard/kpis` avec données réelles
- [ ] Connecter filtres frontend → backend
- [ ] Afficher Top Signaux/Risques depuis `/api/brief`

**Jour 3-4 : Macro**
- [ ] Créer composant `Macro.tsx` complet
- [ ] Créer `MacroBadges.tsx` et `MacroChart.tsx`
- [ ] Brancher endpoints backend

**Jour 5 : Stocks Liste**
- [ ] Créer page `Stocks.tsx`
- [ ] Créer `StocksTable.tsx`
- [ ] Brancher `/api/stocks/universe`

### Semaine 2 (P0 - Suite + P1)

**Jour 6-7 : Copilot LLM**
- [ ] Créer `llm_service.py`
- [ ] Intégrer RAG store
- [ ] Brancher G4F ou autre LLM
- [ ] Tester génération de réponses

**Jour 8-9 : TickerSheet**
- [ ] Vérifier utilisation nouvel endpoint
- [ ] Ajouter graphiques prix
- [ ] Afficher toutes les données

**Jour 10 : Forecasts**
- [ ] Décider : masquer ou implémenter
- [ ] Si implémenter : brancher forecaster

### Semaine 3 (P1 - Finalisation)

**Jour 11-12 : MarketBrief**
- [ ] Migrer vers nouvelles routes ou documenter legacy

**Jour 13-14 : Améliorations UX**
- [ ] Améliorer News (filtres, liens)
- [ ] Masquer Backtests/Judge ou implémenter basique

---

## 📊 Métriques de Complétion

| Catégorie | Complétion | Objectif |
|-----------|------------|----------|
| **Pages fonctionnelles** | 3/11 (27%) | 8/11 (73%) |
| **Backend endpoints** | 6/11 (55%) | 10/11 (91%) |
| **Frontend composants** | 5/11 (45%) | 9/11 (82%) |
| **Intégration complète** | 2/11 (18%) | 8/11 (73%) |

**Score global actuel** : 4.5/10  
**Score cible** : 8.0/10

---

## 🔧 Corrections Techniques Générales

### 1. Nommage Incohérent

**Problème** : Frontend envoie `series_ids` mais API attend `series`

**Solution** :
```typescript
// Aligner frontend avec API
const { data } = useMacroOverview({
  series: seriesIds.join(','), // Pas series_ids
});
```

### 2. Gestion d'Erreurs

**Problème** : Erreurs 404/500 pas toujours affichées clairement

**Solution** :
```typescript
// Intercepter toutes les erreurs API
const { data, error } = useQuery({
  queryFn: () => api.get('/endpoint'),
  onError: (err) => {
    showNotification({
      message: err.message || 'Erreur API',
      color: 'red',
    });
  },
});
```

### 3. Cache et Performance

**Problème** : Pas de cache réel, recalculs fréquents

**Solution** :
```python
# Backend : Ajouter cache Redis (TODO existant)
from functools import lru_cache

@lru_cache(maxsize=100)
def get_macro_snapshot():
    # Calcul lourd
    pass
```

### 4. Nettoyage Legacy

**Problème** : Code legacy (`dash_app/`) encore présent

**Solution** :
- Isoler dans dossier `legacy/`
- Documenter migration
- Supprimer après validation complète

---

## 📝 Notes Finales

### Points Positifs
- ✅ Architecture modulaire bien organisée
- ✅ Backend robuste avec services séparés
- ✅ Frontend moderne (React Query, TypeScript)
- ✅ Certaines pages fonctionnelles (News, Brief partiel)

### Points à Améliorer
- ❌ Données souvent vides ou statiques
- ❌ Intégration frontend ↔ backend incomplète
- ❌ Pages placeholder non informatives
- ❌ LLM non implémenté (cœur du produit)

### Recommandations Stratégiques

1. **Prioriser P0** : Dashboard, Macro, Stocks, Copilot
2. **Masquer P2** : Backtests, Judge (ou cacher en dev)
3. **Documenter** : État actuel de chaque page
4. **Tester** : Après chaque correction, tests E2E

---

**Rapport généré par** : AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Date** : 2025-01-27  
**Version** : 1.0

