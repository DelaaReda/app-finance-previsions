# 🗺️ Finance Copilot - Roadmap Complète des Tâches

**Date** : 2025-01-27  
**Source** : Liste détaillée de tâches pour toutes les pages  
**Analyste** : AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Type** : Planification technique complète (Frontend + Backend + Optimisations)

---

## 🎯 Vue d'Ensemble

**Objectif** : Transformer le MVP partiellement fictif en application complète, performante et robuste avec données réelles.

**Portée** : 8 domaines principaux + optimisations transverses  
**Estimation totale** : ~120-150 heures de développement  
**Priorité globale** : P0 (Critique) pour MVP fonctionnel

---

## 📊 Tableau de Bord des Tâches

| Domaine | Tâches | Priorité | Effort | Statut |
|---------|--------|----------|--------|--------|
| **Dashboard** | 3 | P0 | 12h | 🔴 À faire |
| **Macro** | 2 | P0 | 10h | 🔴 À faire |
| **Stocks** | 3 | P0 | 14h | 🔴 À faire |
| **News** | 3 | P1 | 8h | 🟡 Partiel |
| **Forecasts** | 2 | P1 | 12h | 🔴 À faire |
| **Judge** | 2 | P2 | 6h | 🔴 À faire |
| **Copilot** | 2 | P0 | 16h | 🔴 À faire |
| **Optimisations** | 4 | P1 | 20h | 🟡 Partiel |

**Total** : **21 tâches** | **~98 heures** (sans optimisations) | **~118 heures** (avec optimisations)

---

## 🏠 Dashboard & Page d'Accueil

### Tâche 1.1 : Corriger et Optimiser l'API Dashboard

**Priorité** : P0 🔴  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/dashboard.py` (créer ou modifier)
- `copilot-app/frontend/webapp/src/hooks/useDashboardKPIs.ts`
- `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`

**Description** :
Aligner la réponse de `/api/dashboard/kpis` avec les attentes frontend en incluant `top_signals` et `top_risks`. Si impossible côté backend, adapter le frontend pour appels séparés.

**Solution Backend** :
```python
# copilot-app/backend/api/routes/dashboard.py
@router.get("/dashboard/kpis")
def get_dashboard_kpis():
    """Retourner KPIs + top signaux/risques."""
    # Récupérer KPIs
    forecasts = load_forecasts()
    kpis = {
        "last_forecast_dt": forecasts.get('last_update') if forecasts else None,
        "total_forecasts": len(forecasts.get('data', {}).get('rows', [])) if forecasts else 0,
        "tickers_tracked": len(set([f.get('ticker') for f in forecasts.get('data', {}).get('rows', [])])) if forecasts else 0,
        "available_horizons": ["1d", "1w", "1m", "3m"],
    }
    
    # Récupérer top signaux/risques depuis brief
    brief = load_weekly_brief()
    top_signals = brief.get('data', {}).get('top_signals', [])[:3] if brief else []
    top_risks = brief.get('data', {}).get('top_risks', [])[:3] if brief else []
    
    return {
        **kpis,
        "top_signals": top_signals,
        "top_risks": top_risks,
    }
```

**Solution Frontend (si backend non modifiable)** :
```typescript
// copilot-app/frontend/webapp/src/pages/Dashboard.tsx
const { data: kpis } = useDashboardKPIs();
const { data: brief } = useBrief({ period: 'daily' });

// Combiner les données
const dashboardData = {
  ...kpis,
  topSignals: brief?.top_signals?.slice(0, 3) || [],
  topRisks: brief?.top_risks?.slice(0, 3) || [],
};
```

**Critères de succès** :
- ✅ Endpoint retourne KPIs + signaux/risques
- ✅ Frontend affiche toutes les données
- ✅ Pas de données manquantes dans l'UI

---

### Tâche 1.2 : Pré-calculer et Mettre en Cache les Métriques

**Priorité** : P0 🔴  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/jobs/dashboard_refresh.py` (créer)
- `copilot-app/backend/services/cache_service.py`
- `copilot-app/backend/scheduler/app.py`

**Description** :
Pré-calculer les agrégats du dashboard au démarrage ou via tâche planifiée. Stocker en cache (mémoire ou base) pour améliorer le temps de réponse.

**Solution** :
```python
# copilot-app/backend/jobs/dashboard_refresh.py
def refresh_dashboard_cache():
    """Pré-calculer et mettre en cache les métriques dashboard."""
    # Calculer KPIs
    forecasts = load_forecasts()
    kpis = calculate_kpis(forecasts)
    
    # Récupérer top signaux/risques
    brief = load_weekly_brief()
    top_signals = extract_top_signals(brief, limit=3)
    top_risks = extract_top_risks(brief, limit=3)
    
    # Stocker en cache
    cache_data = {
        "kpis": kpis,
        "top_signals": top_signals,
        "top_risks": top_risks,
        "cached_at": datetime.utcnow().isoformat(),
    }
    save_json(cache_data, "dashboard_cache.json")
    
    return cache_data

# Dans scheduler/app.py
scheduler.add_job(
    refresh_dashboard_cache,
    "interval",
    minutes=15,  # Rafraîchir toutes les 15 min
)
```

**Cache HTTP** :
```python
# Ajouter headers de cache
@router.get("/dashboard/kpis")
def get_dashboard_kpis():
    data = load_dashboard_cache()  # Charger depuis cache
    return Response(
        content=json.dumps(data),
        headers={
            "Cache-Control": "public, max-age=300",  # 5 min
            "ETag": generate_etag(data),
        }
    )
```

**Critères de succès** :
- ✅ Métriques pré-calculées au démarrage
- ✅ Cache rafraîchi toutes les 15 min
- ✅ Temps de réponse < 100ms

---

### Tâche 1.3 : Limiter le Chargement Initial

**Priorité** : P1 🟡  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/pages/Dashboard.tsx`
- `copilot-app/frontend/webapp/src/components/dashboard/`
- `copilot-app/frontend/webapp/vite.config.ts`

**Description** :
S'assurer que la page d'accueil ne charge pas toutes les données dès l'ouverture. Utiliser code splitting et lazy loading.

**Solution** :
```typescript
// copilot-app/frontend/webapp/src/pages/Dashboard.tsx
import { lazy, Suspense } from 'react';

// Lazy load des composants non critiques
const DashboardFilters = lazy(() => import('./components/DashboardFilters'));
const TopSignals = lazy(() => import('./components/TopSignals'));
const TopRisks = lazy(() => import('./components/TopRisks'));

export default function Dashboard() {
  // Charger KPIs immédiatement (critique)
  const { data: kpis } = useDashboardKPIs();
  
  // Charger signaux/risques après affichage initial
  const { data: signals } = useTopSignals({ enabled: !!kpis });
  const { data: risks } = useTopRisks({ enabled: !!kpis });
  
  return (
    <Container>
      {/* KPIs critiques chargés immédiatement */}
      <KPIsGrid data={kpis} />
      
      {/* Composants lazy loadés */}
      <Suspense fallback={<Skeleton />}>
        <DashboardFilters />
        <TopSignals data={signals} />
        <TopRisks data={risks} />
      </Suspense>
    </Container>
  );
}
```

**Code Splitting Vite** :
```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'dashboard': ['./src/pages/Dashboard.tsx'],
          'charts': ['recharts'],
        },
      },
    },
  },
});
```

**Critères de succès** :
- ✅ Bundle initial < 200KB
- ✅ Affichage initial < 1s
- ✅ Composants non critiques chargés après

---

## 📈 Page Macro

### Tâche 2.1 : Intégrer les Séries Macro avec Graphiques

**Priorité** : P0 🔴  
**Effort** : 6h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/pages/Macro.tsx` (créer)
- `copilot-app/frontend/webapp/src/components/macro/MacroChart.tsx` (créer)
- `copilot-app/frontend/webapp/src/hooks/useMacro.ts`
- `copilot-app/frontend/webapp/src/services/macro.service.ts`

**Description** :
Connecter la page macro aux vraies données et remplacer les placeholders par des graphiques dynamiques (Recharts).

**Solution** :
```typescript
// copilot-app/frontend/webapp/src/pages/Macro.tsx
import { lazy, Suspense } from 'react';
import { useMacroSnapshot, useMacroOverview } from '@/hooks/useMacro';

const MacroChart = lazy(() => import('@/components/macro/MacroChart'));

export default function Macro() {
  const { data: snapshot, isLoading } = useMacroSnapshot();
  const { data: overview } = useMacroOverview({ 
    range: '5y',
    series: 'CPIAUCSL,UNRATE,DGS10', // Corriger: utiliser 'series' pas 'series_ids'
  });
  
  if (isLoading) return <LoadingSpinner />;
  if (!snapshot) return <EmptyState />;
  
  return (
    <Container>
      <PageHeader title="Macro" />
      
      {/* Badges z-scores */}
      <MacroBadges zscores={snapshot.zscores} />
      
      {/* Graphique lazy loadé */}
      <Suspense fallback={<ChartSkeleton />}>
        <MacroChart 
          data={overview?.series}
          source={snapshot.trace?.source}
          lastUpdate={snapshot.trace?.generated_at}
        />
      </Suspense>
    </Container>
  );
}
```

**Correction Paramètre API** :
```typescript
// copilot-app/frontend/webapp/src/services/macro.service.ts
export const macroService = {
  async getOverview(params: { range: string; series: string }) {
    // Utiliser 'series' pas 'series_ids' pour correspondre à l'API
    return apiGet<MacroOverview>('/api/macro/overview', {
      range: params.range,
      series: params.series, // ✅ Correct
    });
  },
};
```

**Composant Graphique** :
```typescript
// copilot-app/frontend/webapp/src/components/macro/MacroChart.tsx
import { LineChart, Line, XAxis, YAxis, Legend, ResponsiveContainer } from 'recharts';

export function MacroChart({ data, source, lastUpdate }) {
  return (
    <Card>
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data}>
          <XAxis dataKey="date" />
          <YAxis />
          <Legend />
          <Line type="monotone" dataKey="CPIAUCSL" stroke="#8884d8" />
          <Line type="monotone" dataKey="UNRATE" stroke="#82ca9d" />
          <Line type="monotone" dataKey="DGS10" stroke="#ffc658" />
        </LineChart>
      </ResponsiveContainer>
      <Text size="sm" c="dimmed" mt="md">
        Source: {source} | Last update: {lastUpdate}
      </Text>
    </Card>
  );
}
```

**Critères de succès** :
- ✅ Page affiche données macro réelles
- ✅ Graphiques dynamiques fonctionnels
- ✅ Paramètre API corrigé (series vs series_ids)
- ✅ Lazy loading des graphiques

---

### Tâche 2.2 : Caching des Données Macro

**Priorité** : P1 🟡  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/services/cache_service.py`
- `copilot-app/backend/api/routes/macro.py`
- `copilot-app/frontend/webapp/src/hooks/useMacro.ts`

**Description** :
Mettre en cache côté serveur les séries macro (peu volatiles) pour éviter requêtes FRED répétées.

**Solution Backend** :
```python
# copilot-app/backend/services/cache_service.py
from functools import lru_cache
from datetime import datetime, timedelta

class MacroCache:
    _cache = {}
    _cache_ttl = timedelta(hours=1)
    
    @classmethod
    def get(cls, key):
        """Récupérer depuis cache si valide."""
        if key in cls._cache:
            data, timestamp = cls._cache[key]
            if datetime.utcnow() - timestamp < cls._cache_ttl:
                return data
        return None
    
    @classmethod
    def set(cls, key, data):
        """Stocker en cache."""
        cls._cache[key] = (data, datetime.utcnow())

# Dans api/routes/macro.py
@router.get("/macro/overview")
def get_macro_overview(series: str, range: str = "5y"):
    cache_key = f"macro_overview_{series}_{range}"
    
    # Vérifier cache
    cached = MacroCache.get(cache_key)
    if cached:
        return cached
    
    # Calculer si pas en cache
    data = macro_service.get_macro_overview(series, range)
    
    # Mettre en cache
    MacroCache.set(cache_key, data)
    
    return data
```

**Solution Frontend** :
```typescript
// staleTime déjà configuré à 1h dans useMacro.ts
const { data } = useQuery({
  queryKey: ['macro', 'overview', params],
  queryFn: () => macroService.getOverview(params),
  staleTime: 3600000, // 1h ✅ Déjà présent
});
```

**Critères de succès** :
- ✅ Cache serveur actif (1h TTL)
- ✅ Cache client configuré (1h staleTime)
- ✅ Réduction requêtes FRED de 90%+

---

## 📊 Page Actions (Stocks)

### Tâche 3.1 : Remplacer Données Factices par Vraies API

**Priorité** : P0 🔴  
**Effort** : 6h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/stocks.py` (créer ou modifier)
- `copilot-app/frontend/webapp/src/services/stocks.service.ts`
- `copilot-app/frontend/webapp/src/pages/Stocks.tsx`

**Description** :
Créer endpoints backend pour recherche et analyse de tickers, remplacer les mocks frontend.

**Solution Backend** :
```python
# copilot-app/backend/api/routes/stocks.py
@router.get("/stocks/search")
def search_stocks(q: str = Query(..., min_length=2)):
    """Rechercher tickers par nom ou symbole."""
    # Recherche dans base de tickers
    results = stock_service.search_tickers(q)
    return {"results": results}

@router.get("/stocks/{ticker}")
def get_stock_analysis(
    ticker: str,
    features: str = "all",
    range: str = "1y",
):
    """Analyse complète d'un ticker."""
    # Récupérer prix
    prices = get_price_history(ticker, period=range)
    
    # Calculer indicateurs
    indicators = compute_indicators(prices)
    
    # Récupérer signaux
    signals = get_trading_signals(ticker, indicators)
    
    # Calculer score composite
    composite_score = calculate_composite_score(
        macro_score=get_macro_score(ticker),
        tech_score=indicators.get('rsi_score', 0),
        news_score=get_news_sentiment(ticker),
    )
    
    return {
        "ticker": ticker,
        "prices": prices,
        "indicators": indicators,
        "signals": signals,
        "composite_score": composite_score,
    }
```

**Solution Frontend** :
```typescript
// copilot-app/frontend/webapp/src/services/stocks.service.ts
export const stocksService = {
  async search(query: string): Promise<StockSearchResult[]> {
    // ✅ Remplacer mock par vrai appel
    return apiGet<StockSearchResult[]>('/api/stocks/search', { q: query });
  },
  
  async getAnalysis(ticker: string): Promise<StockAnalysis> {
    // ✅ Remplacer mock par vrai appel
    return apiGet<StockAnalysis>(`/api/stocks/${ticker}`, {
      features: 'all',
      range: '1y',
    });
  },
};
```

**Critères de succès** :
- ✅ Endpoints backend fonctionnels
- ✅ Frontend utilise vraies données
- ✅ Plus de mocks dans stocks.service.ts

---

### Tâche 3.2 : Optimiser la Recherche d'Actions

**Priorité** : P1 🟡  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/components/stocks/StockSearch.tsx`
- `copilot-app/backend/api/routes/stocks.py`
- `copilot-app/backend/services/stock_screener.py`

**Description** :
Ajouter debounce côté frontend, optimiser recherche backend (index, cache).

**Solution Frontend** :
```typescript
// copilot-app/frontend/webapp/src/components/stocks/StockSearch.tsx
import { useDebouncedValue } from '@mantine/hooks';

export function StockSearch() {
  const [query, setQuery] = useState('');
  const [debouncedQuery] = useDebouncedValue(query, 300); // 300ms debounce
  
  const { data, isLoading } = useQuery({
    queryKey: ['stocks', 'search', debouncedQuery],
    queryFn: () => stocksService.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2, // ✅ Déjà présent
  });
  
  return (
    <TextInput
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="Rechercher un ticker (min 2 caractères)"
    />
  );
}
```

**Solution Backend** :
```python
# copilot-app/backend/services/stock_screener.py
from functools import lru_cache

@lru_cache(maxsize=1000)
def search_tickers_cached(query: str):
    """Recherche avec cache LRU."""
    # Recherche indexée si possible
    results = ticker_database.search(query)
    return results

# Dans api/routes/stocks.py
@router.get("/stocks/search")
def search_stocks(q: str = Query(..., min_length=2, max_length=50)):
    # Limiter longueur pour éviter abus
    if len(q) > 50:
        raise HTTPException(400, "Query too long")
    
    results = search_tickers_cached(q.upper())
    return {"results": results[:20]}  # Limiter à 20 résultats
```

**Critères de succès** :
- ✅ Debounce 300ms côté frontend
- ✅ Cache LRU côté backend
- ✅ Limite de résultats (20 max)
- ✅ Validation longueur query

---

### Tâche 3.3 : Brancher l'Analyse Technique sur Données Réelles

**Priorité** : P0 🔴  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/stocks.py`
- `copilot-app/frontend/webapp/src/pages/TickerSheet.tsx`
- `copilot-app/frontend/webapp/src/components/stocks/StockAnalysis.tsx`

**Description** :
Vérifier que l'endpoint `/api/stocks/{ticker}` fournit toutes les données attendues par le frontend.

**Solution** :
```python
# S'assurer que la réponse correspond au type StockAnalysis
@router.get("/stocks/{ticker}")
def get_stock_analysis(ticker: str):
    return {
        "ticker": ticker,
        "current_price": prices[-1].close,
        "change_1d": calculate_change(prices, "1d"),
        "change_1w": calculate_change(prices, "1w"),
        "change_1m": calculate_change(prices, "1m"),
        "indicators": {
            "sma_20": indicators["sma_20"],
            "sma_50": indicators["sma_50"],
            "sma_200": indicators["sma_200"],
            "rsi": indicators["rsi"],
            "macd": indicators["macd"],
        },
        "signals": [
            {"type": "buy", "strength": 0.8, "reason": "RSI oversold"},
        ],
        "composite_score": 72,  # ✅ Inclure dans réponse
    }
```

**Vérification Frontend** :
```typescript
// Tester avec AAPL
const { data } = useStockAnalysis('AAPL');

// Vérifier que toutes les sections se peuplent
console.assert(data.composite_score !== undefined);
console.assert(data.indicators.rsi !== undefined);
console.assert(data.signals.length > 0);
```

**Critères de succès** :
- ✅ Toutes les métriques affichées
- ✅ Score composite visible
- ✅ Signaux de trading présents
- ✅ Test avec AAPL réussi

---

## 🗞️ Page Actualités (News)

### Tâche 4.1 : S'assurer du Bon Fonctionnement de la Pagination

**Priorité** : P1 🟡  
**Effort** : 3h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/news.py`
- `copilot-app/frontend/webapp/src/hooks/useNews.ts`

**Description** :
Vérifier que l'API supporte pagination (page, limit) et tester le bouton "Charger plus".

**Solution Backend** :
```python
# copilot-app/backend/api/routes/news.py
@router.get("/news/feed")
def get_news_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    tickers: Optional[str] = None,
    since: Optional[str] = None,
):
    """Retourner news paginées."""
    offset = (page - 1) * limit
    
    # Récupérer news avec offset
    news = news_service.get_news(
        offset=offset,
        limit=limit,
        tickers=tickers.split(',') if tickers else None,
        since=since,
    )
    
    # Vérifier s'il y a une page suivante
    total = news_service.count_news(tickers, since)
    has_more = offset + limit < total
    
    return {
        "articles": news,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "has_more": has_more,
        },
    }
```

**Solution Frontend** :
```typescript
// copilot-app/frontend/webapp/src/hooks/useNews.ts
export function useNews(filters?: NewsFilters) {
  const [page, setPage] = useState(1);
  
  const { data, isLoading } = useQuery({
    queryKey: ['news', filters, page],
    queryFn: () => api.get('/api/news/feed', {
      page,
      limit: 50,
      ...filters,
    }),
  });
  
  const loadMore = () => {
    if (data?.pagination?.has_more) {
      setPage(p => p + 1);
    }
  };
  
  return {
    articles: data?.articles || [],
    hasMore: data?.pagination?.has_more || false,
    loadMore,
    isLoading,
  };
}
```

**Critères de succès** :
- ✅ Pagination fonctionnelle (page, limit)
- ✅ Bouton "Charger plus" charge page suivante
- ✅ Pas de doublons entre pages
- ✅ Indicateur has_more correct

---

### Tâche 4.2 : Implémenter les Filtres de News Côté Backend

**Priorité** : P1 🟡  
**Effort** : 3h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/news.py`
- `copilot-app/backend/services/news_service.py`

**Description** :
Implémenter filtrage par ticker, mot-clé, plage de dates dans l'API.

**Solution** :
```python
# copilot-app/backend/api/routes/news.py
@router.get("/news/feed")
def get_news_feed(
    tickers: Optional[str] = None,
    q: Optional[str] = None,  # Keyword search
    start: Optional[str] = None,  # Date début
    end: Optional[str] = None,  # Date fin
):
    """Filtrer news selon critères."""
    filters = {}
    
    if tickers:
        filters['tickers'] = [t.strip().upper() for t in tickers.split(',')]
    
    if q:
        filters['keyword'] = q  # Recherche full-text
    
    if start:
        filters['start_date'] = parse_date(start)
    
    if end:
        filters['end_date'] = parse_date(end)
    
    news = news_service.get_filtered_news(filters)
    return {"articles": news}
```

**Critères de succès** :
- ✅ Filtre par ticker fonctionnel
- ✅ Recherche par mot-clé fonctionnelle
- ✅ Filtre par dates fonctionnel
- ✅ Frontend réinitialise liste au changement filtre

---

### Tâche 4.3 : Optimiser le Chargement des Composants News

**Priorité** : P2 🟢  
**Effort** : 2h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/pages/News.tsx`
- `copilot-app/frontend/webapp/src/components/news/NewsFilters.tsx`

**Description** :
Conserver React.Suspense pour lazy loading, améliorer gestion des états.

**Solution** :
```typescript
// Déjà présent, s'assurer que c'est bien utilisé
const NewsFilters = lazy(() => import('./components/news/NewsFilters'));

export default function News() {
  return (
    <Container>
      <Suspense fallback={<FiltersSkeleton />}>
        <NewsFilters />
      </Suspense>
      
      {/* Liste principale chargée immédiatement */}
      <NewsFeed />
    </Container>
  );
}
```

**Critères de succès** :
- ✅ Lazy loading des filtres actif
- ✅ Spinner "Chargement..." visible
- ✅ Message "Aucune news" si vide

---

## 🔮 Page Prévisions (Forecasts)

### Tâche 5.1 : Créer API pour Prévisions Multi-Actifs

**Priorité** : P1 🟡  
**Effort** : 8h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/forecasts.py`
- `copilot-app/backend/services/forecast_service.py`
- `copilot-app/backend/models/forecast_hybrid_v1.py`

**Description** :
Développer endpoint `/api/forecasts` qui lit résultats pré-calculés (Parquet) et supporte filtres.

**Solution** :
```python
# copilot-app/backend/api/routes/forecasts.py
@router.get("/forecasts")
def get_forecasts(
    asset_type: Optional[str] = None,  # equity|commodity|all
    horizon: Optional[str] = None,  # 1w|1m|1y
    ticker: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    """Retourner prévisions avec filtres."""
    # Charger depuis Parquet
    forecasts_df = pd.read_parquet("data/forecasts.parquet")
    
    # Appliquer filtres
    if asset_type and asset_type != "all":
        forecasts_df = forecasts_df[forecasts_df['asset_type'] == asset_type]
    
    if horizon:
        forecasts_df = forecasts_df[forecasts_df['horizon'] == horizon]
    
    if ticker:
        forecasts_df = forecasts_df[forecasts_df['ticker'] == ticker.upper()]
    
    # Limiter résultats
    forecasts_df = forecasts_df.head(limit)
    
    # Convertir en JSON
    forecasts = forecasts_df.to_dict('records')
    
    return {
        "rows": forecasts,
        "count": len(forecasts),
        "filters_applied": {
            "asset_type": asset_type,
            "horizon": horizon,
            "ticker": ticker,
        },
    }
```

**Critères de succès** :
- ✅ Endpoint lit depuis Parquet
- ✅ Filtres fonctionnels
- ✅ Limite de résultats respectée
- ✅ Format JSON cohérent

---

### Tâche 5.2 : Construire Page Forecasts Côté Frontend

**Priorité** : P1 🟡  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/pages/Forecasts.tsx`
- `copilot-app/frontend/webapp/src/components/forecasts/ForecastsTable.tsx`
- `copilot-app/frontend/webapp/src/hooks/useForecasts.ts`

**Description** :
Créer composant page avec filtres (type actif, horizon, recherche) et tableau de prévisions.

**Solution** :
```typescript
// copilot-app/frontend/webapp/src/pages/Forecasts.tsx
export default function Forecasts() {
  const [filters, setFilters] = useState({
    assetType: 'all',
    horizon: null,
    ticker: '',
  });
  
  const { data, isLoading } = useForecasts(filters);
  
  return (
    <Container>
      <PageHeader title="Prévisions" />
      
      {/* Filtres */}
      <ForecastsFilters 
        filters={filters}
        onChange={setFilters}
      />
      
      {/* Tableau */}
      <ForecastsTable 
        data={data?.rows || []}
        isLoading={isLoading}
      />
    </Container>
  );
}
```

**Critères de succès** :
- ✅ Filtres fonctionnels
- ✅ Tableau paginé ou limité
- ✅ Tri par score/confiance
- ✅ Performance acceptable (< 1s chargement)

---

## 🤖 Page Judge (LLM)

### Tâche 6.1 : Exposer Résultats LLM Judge

**Priorité** : P2 🟢  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/api/routes/judge.py` (créer)
- `copilot-app/backend/models/llm_ranker.py`

**Description** :
Créer endpoint `/api/forecasts/judge` qui lit verdicts LLM pré-calculés.

**Solution** :
```python
# copilot-app/backend/api/routes/judge.py
@router.get("/forecasts/judge")
def get_judge_results():
    """Retourner verdicts LLM pré-calculés."""
    # Lire depuis fichier JSON/JSONL produit par agent
    judge_results = load_json("data/judge_results.json")
    
    if not judge_results:
        return {"rows": [], "count": 0}
    
    return {
        "rows": judge_results.get("results", []),
        "count": len(judge_results.get("results", [])),
        "generated_at": judge_results.get("generated_at"),
    }
```

**Critères de succès** :
- ✅ Endpoint retourne verdicts LLM
- ✅ Format cohérent avec ancienne UI
- ✅ Pas de calcul en temps réel

---

### Tâche 6.2 : Interface Frontend pour Verdict LLM

**Priorité** : P2 🟢  
**Effort** : 2h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/pages/Judge.tsx`
- `copilot-app/frontend/webapp/src/components/judge/JudgeTable.tsx`

**Description** :
Créer page avec tableau des tickers et verdicts LLM (flèches vertes/rouges).

**Solution** :
```typescript
// copilot-app/frontend/webapp/src/pages/Judge.tsx
export default function Judge() {
  const { data } = useJudgeResults();
  
  return (
    <Container>
      <PageHeader title="LLM Judge" />
      
      <JudgeTable 
        data={data?.rows || []}
        // Highlighting conditionnel
        rowStyle={(row) => ({
          backgroundColor: row.direction === 'up' ? '#e8f5e9' : 
                          row.direction === 'down' ? '#ffebee' : '#f5f5f5',
        })}
      />
    </Container>
  );
}
```

**Critères de succès** :
- ✅ Tableau avec verdicts affiché
- ✅ Highlighting conditionnel (vert/rouge)
- ✅ Lazy loading du composant
- ✅ Bouton rafraîchir si nécessaire

---

## 💬 Assistant Copilot (Q&A)

### Tâche 7.1 : Connecter Module Q&A à Vrai LLM

**Priorité** : P0 🔴  
**Effort** : 10h  
**Fichiers concernés** :
- `copilot-app/backend/services/llm_service.py` (créer)
- `copilot-app/backend/api/routes/copilot.py`
- `copilot-app/backend/services/rag_service.py`

**Description** :
Implémenter client LLM Python et brancher endpoint `/api/copilot/ask`.

**Solution** :
```python
# copilot-app/backend/services/llm_service.py
from g4f.client import Client

class LLMService:
    def __init__(self):
        self.client = Client()
    
    async def generate_response(
        self,
        question: str,
        context: List[Dict],
        model: str = "gpt-4",
    ):
        """Générer réponse LLM avec contexte RAG."""
        # Construire prompt avec contexte
        prompt = self._build_prompt(question, context)
        
        # Appeler LLM
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        
        # Extraire sources
        sources = [c.get("source") for c in context]
        
        return {
            "text": response.choices[0].message.content,
            "sources": sources,
            "confidence": self._calculate_confidence(response),
        }

# copilot-app/backend/api/routes/copilot.py
@router.post("/copilot/ask")
async def ask_copilot(request: CopilotRequest):
    """Générer réponse LLM avec RAG."""
    # Rechercher contexte RAG
    context = rag_service.search_context(request.question, limit=5)
    
    # Générer réponse
    llm_service = LLMService()
    response = await llm_service.generate_response(
        question=request.question,
        context=context,
    )
    
    return response
```

**Critères de succès** :
- ✅ Client LLM fonctionnel (G4F ou autre)
- ✅ RAG store intégré
- ✅ Réponses avec sources
- ✅ Gestion erreurs/timeout

---

### Tâche 7.2 : Finaliser Intégration Frontend Copilot

**Priorité** : P0 🔴  
**Effort** : 6h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/services/copilot.service.ts`
- `copilot-app/frontend/webapp/src/pages/Copilot.tsx`

**Description** :
Ajouter méthodes `getRAGStats()` et `createSession()`, implémenter streaming si possible.

**Solution** :
```typescript
// copilot-app/frontend/webapp/src/services/copilot.service.ts
export const copilotService = {
  async ask(question: string, sessionId?: string) {
    return apiPost<CopilotResponse>('/api/copilot/ask', {
      question,
      session_id: sessionId,
    });
  },
  
  async getRAGStats() {
    return apiGet<RAGStats>('/api/rag/stats');
  },
  
  async createSession() {
    return apiPost<Session>('/api/copilot/session');
  },
};
```

**Streaming (optionnel)** :
```typescript
// Si backend supporte streaming
async function* askStreaming(question: string) {
  const response = await fetch('/api/copilot/ask/stream', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
  
  const reader = response.body.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    yield new TextDecoder().decode(value);
  }
}
```

**Critères de succès** :
- ✅ Méthodes getRAGStats/createSession implémentées
- ✅ Page Copilot fonctionnelle
- ✅ Indicateur de chargement visible
- ✅ Streaming ou réponse complète

---

## ⚙️ Optimisations Transverses

### Tâche 8.1 : Gestion des Erreurs et Validation

**Priorité** : P1 🟡  
**Effort** : 6h  
**Fichiers concernés** :
- `copilot-app/frontend/webapp/src/api/client.ts`
- `copilot-app/backend/api/main.py`
- Tous les endpoints

**Description** :
Centraliser gestion erreurs frontend, validation stricte backend (Pydantic).

**Solution Frontend** :
```typescript
// copilot-app/frontend/webapp/src/api/client.ts
export async function apiGet<T>(path: string, params?: any) {
  try {
    const response = await fetch(buildUrl(path, params));
    
    if (!response.ok) {
      // Gestion centralisée
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new ApiError(response.status, error.message || 'API Error');
    }
    
    return await response.json();
  } catch (error) {
    // Logger et afficher notification
    console.error('API Error:', error);
    showNotification({
      message: error.message || 'Erreur réseau',
      color: 'red',
    });
    throw error;
  }
}
```

**Solution Backend** :
```python
# Validation Pydantic stricte
from pydantic import BaseModel, validator

class MacroRequest(BaseModel):
    series: str
    range: str = "5y"
    
    @validator('series')
    def validate_series(cls, v):
        if not v or len(v.split(',')) > 10:
            raise ValueError('Max 10 series')
        return v
    
    @validator('range')
    def validate_range(cls, v):
        allowed = ['1y', '5y', '10y']
        if v not in allowed:
            raise ValueError(f'Range must be in {allowed}')
        return v
```

**Critères de succès** :
- ✅ Gestion erreurs centralisée frontend
- ✅ Validation Pydantic sur tous endpoints
- ✅ Messages d'erreur clairs
- ✅ Codes HTTP appropriés (4xx/5xx)

---

### Tâche 8.2 : Rate Limiting et Sécurité

**Priorité** : P1 🟡  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/api/middleware/rate_limit.py` (créer)
- `copilot-app/backend/api/main.py`

**Description** :
Implémenter rate limiting sur endpoints critiques, configurer CORS pour prod.

**Solution** :
```python
# copilot-app/backend/api/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Dans main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Appliquer sur endpoints
@router.post("/copilot/ask")
@limiter.limit("5/minute")  # 5 requêtes par minute
async def ask_copilot(request: Request, ...):
    pass

@router.get("/news/feed")
@limiter.limit("30/minute")
def get_news_feed(...):
    pass
```

**CORS Production** :
```python
# Dans main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Critères de succès** :
- ✅ Rate limiting actif (5/min copilot, 30/min news)
- ✅ CORS configuré pour prod
- ✅ Exceptions personnalisées
- ✅ Tests de charge réussis

---

### Tâche 8.3 : Optimisation RAG Store

**Priorité** : P2 🟢  
**Effort** : 6h  
**Fichiers concernés** :
- `copilot-app/backend/services/rag_service.py`
- `copilot-app/backend/storage/rag_store.py`

**Description** :
Améliorer recherche RAG (SQLite FTS5 ou base vectorielle).

**Solution SQLite FTS5** :
```python
# copilot-app/backend/storage/rag_store.py
import sqlite3

class RAGStore:
    def __init__(self, db_path="data/rag.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_fts5()
    
    def _init_fts5(self):
        """Créer table FTS5 pour recherche full-text."""
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
                id, title, content, source, published
            );
        """)
    
    def search(self, query: str, limit: int = 5):
        """Recherche full-text rapide."""
        cursor = self.conn.execute("""
            SELECT * FROM news_fts
            WHERE news_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        return [dict(row) for row in cursor]
```

**Critères de succès** :
- ✅ Recherche RAG < 100ms (vs O(n) avant)
- ✅ Index FTS5 créé
- ✅ Tests de performance réussis

---

### Tâche 8.4 : Tests et Monitoring

**Priorité** : P1 🟡  
**Effort** : 4h  
**Fichiers concernés** :
- `copilot-app/backend/tests/`
- `copilot-app/frontend/webapp/tests/`
- `copilot-app/backend/api/routes/health.py`

**Description** :
Tests E2E manuels, tests automatisés API, monitoring performance.

**Solution Tests API** :
```python
# copilot-app/backend/tests/test_api.py
def test_dashboard_kpis(client):
    response = client.get("/api/dashboard/kpis")
    assert response.status_code == 200
    data = response.json()
    assert "total_forecasts" in data
    assert data["total_forecasts"] >= 0

def test_macro_overview(client):
    response = client.get("/api/macro/overview?series=CPIAUCSL&range=5y")
    assert response.status_code == 200
    data = response.json()
    assert "series" in data
```

**Monitoring** :
```python
# Ajouter métriques dans health endpoint
@router.get("/health")
def health_check():
    return {
        "status": "up",
        "memory_usage": get_memory_usage(),
        "cpu_usage": get_cpu_usage(),
        "cache_hit_rate": cache_service.get_hit_rate(),
    }
```

**Critères de succès** :
- ✅ Tests E2E manuels passés
- ✅ Tests API automatisés (10+ tests)
- ✅ Monitoring basique en place
- ✅ Performance acceptable (< 1s chargement pages)

---

## 📋 Plan d'Exécution Priorisé

### Sprint 1 (Semaine 1) - P0 Critique

**Objectif** : Rendre les pages principales fonctionnelles

- [ ] **Jour 1-2** : Dashboard (Tâches 1.1, 1.2)
- [ ] **Jour 3-4** : Macro (Tâche 2.1)
- [ ] **Jour 5** : Stocks recherche (Tâche 3.1)

**Livrable** : Dashboard et Macro fonctionnels avec vraies données

---

### Sprint 2 (Semaine 2) - P0 Suite

**Objectif** : Finaliser pages critiques

- [ ] **Jour 6-7** : Stocks analyse (Tâche 3.3)
- [ ] **Jour 8-10** : Copilot LLM (Tâche 7.1, 7.2)

**Livrable** : Stocks et Copilot fonctionnels

---

### Sprint 3 (Semaine 3) - P1 Important

**Objectif** : Améliorer qualité et performance

- [ ] **Jour 11-12** : News pagination/filtres (Tâches 4.1, 4.2)
- [ ] **Jour 13-14** : Forecasts (Tâches 5.1, 5.2)
- [ ] **Jour 15** : Optimisations (Tâches 8.1, 8.2)

**Livrable** : Toutes les pages fonctionnelles avec optimisations

---

### Sprint 4 (Semaine 4) - P2 Améliorations

**Objectif** : Finalisation et polish

- [ ] **Jour 16-17** : Judge (Tâches 6.1, 6.2)
- [ ] **Jour 18** : Optimisations RAG (Tâche 8.3)
- [ ] **Jour 19-20** : Tests et monitoring (Tâche 8.4)

**Livrable** : Application complète, testée, optimisée

---

## 📊 Métriques de Succès

| Métrique | Actuel | Cible | Mesure |
|----------|--------|-------|--------|
| **Pages fonctionnelles** | 3/11 (27%) | 10/11 (91%) | Tests E2E |
| **Données réelles** | 30% | 100% | Audit données |
| **Temps chargement** | 2-5s | < 1s | Lighthouse |
| **Taux erreurs API** | 5% | < 1% | Monitoring |
| **Couverture tests** | 10% | 60% | Tests automatisés |

---

## 🎯 Critères d'Acceptation Globaux

### Fonctionnel
- ✅ Toutes les pages affichent des données réelles
- ✅ Plus de mocks dans le code
- ✅ Filtres et pagination fonctionnels partout
- ✅ LLM Copilot génère vraies réponses

### Performance
- ✅ Temps de chargement < 1s pour pages principales
- ✅ Cache actif sur données peu volatiles
- ✅ Code splitting réduit bundle initial < 200KB

### Qualité
- ✅ Gestion erreurs centralisée
- ✅ Validation stricte backend
- ✅ Tests automatisés (60%+ couverture)
- ✅ Monitoring en place

---

**Rapport généré par** : AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Date** : 2025-01-27  
**Version** : 1.0

