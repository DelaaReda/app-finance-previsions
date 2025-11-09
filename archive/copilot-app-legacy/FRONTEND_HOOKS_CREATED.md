# 🎣 Hooks Frontend Créés

**Date**: 2025-01-27  
**Agent**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Total**: **6 hooks React Query** créés

---

## ✅ Hooks Créés

### 1. **useDashboardKPIs** (`useDashboardKPIs.ts`)

**Usage**: Récupère les KPIs du dashboard pour MetricCard et StatsGrid

```tsx
import { useDashboardKPIs } from '@/hooks/useDashboardKPIs';

const Dashboard = () => {
  const { data, isLoading, error } = useDashboardKPIs();
  
  if (isLoading) return <Skeleton />;
  if (error) return <EmptyState />;
  
  return (
    <StatsGrid
      metrics={[
        { label: 'Prévisions', value: data.forecasts.total },
        { label: 'Confiance moy.', value: `${data.forecasts.avg_confidence}%` },
      ]}
    />
  );
};
```

**Endpoint**: `/api/dashboard/kpis`  
**Cache**: 5 minutes stale, 10 minutes cache

---

### 2. **useCorrelationNetwork** (`useCorrelationNetwork.ts`)

**Usage**: Récupère la matrice et le network de corrélations

```tsx
import { useCorrelationMatrix, useCorrelationNetwork } from '@/hooks/useCorrelationNetwork';

// Pour CorrelationHeatmap
const Heatmap = () => {
  const { data } = useCorrelationMatrix();
  // data.matrix, data.tickers
};

// Pour CorrelationNetwork
const Network = () => {
  const { data } = useCorrelationNetwork(0.6); // threshold
  // data.nodes, data.links
};
```

**Endpoints**: 
- `/api/correlations/matrix`
- `/api/correlations/network?threshold=0.5`

**Cache**: 15 minutes stale, 30 minutes cache

---

### 3. **useSectorAllocation** (`useSectorAllocation.ts`)

**Usage**: Récupère l'allocation par secteur pour SectorWheel et TreemapChart

```tsx
import { useSectorAllocation } from '@/hooks/useSectorAllocation';

const Portfolio = () => {
  const { data } = useSectorAllocation();
  
  return (
    <SectorWheel
      data={data.sectors.map(s => ({
        id: s.id,
        label: s.label,
        value: s.value,
        color: s.color,
      }))}
    />
  );
};
```

**Endpoint**: `/api/stocks/sectors`  
**Cache**: 30 minutes stale, 1 hour cache

---

### 4. **useEfficientFrontier** (`useEfficientFrontier.ts`)

**Usage**: Récupère la frontière efficiente pour portfolio optimization

```tsx
import { useEfficientFrontier } from '@/hooks/useEfficientFrontier';

const Optimization = () => {
  const { data } = useEfficientFrontier();
  
  return (
    <EfficientFrontier
      frontier={data.frontier}
      tickers={data.tickers}
    />
  );
};
```

**Endpoint**: `/api/backtests/efficient_frontier`  
**Cache**: 1 hour stale, 2 hours cache

---

### 5. **useCapitalFlows** (`useCapitalFlows.ts`)

**Usage**: Récupère les flux de capitaux pour SankeyDiagram

```tsx
import { useCapitalFlows } from '@/hooks/useCapitalFlows';

const Flows = () => {
  const { data } = useCapitalFlows();
  
  return (
    <SankeyDiagram
      nodes={data.nodes}
      links={data.links}
    />
  );
};
```

**Endpoint**: `/api/flows/capital`  
**Cache**: 15 minutes stale, 30 minutes cache

---

### 6. **useOrderBook** (`useOrderBook.ts`)

**Usage**: Récupère le carnet d'ordres pour un ticker (OrderBook widget)

```tsx
import { useOrderBook } from '@/hooks/useOrderBook';

const Trading = () => {
  const { data, isLoading } = useOrderBook('AAPL', true);
  
  if (isLoading) return <Skeleton />;
  
  return (
    <OrderBook
      bids={data.bids}
      asks={data.asks}
      lastPrice={data.lastPrice}
    />
  );
};
```

**Endpoint**: `/api/orderbook?ticker=AAPL`  
**Cache**: 30 seconds stale, 2 minutes cache  
**Auto-refetch**: Toutes les 10 secondes (pour feeling temps réel)

---

## 📋 Caractéristiques Communes

Tous les hooks suivent le même pattern:

1. **React Query** (`useQuery`) pour le caching et la gestion d'état
2. **Format backend** : Gestion du format `{ok, data}` ou `{data}` direct
3. **Fallback** : Structure vide mais valide si erreur
4. **TypeScript** : Interfaces typées pour toutes les données
5. **Retry logic** : 1-2 tentatives avec délai
6. **Cache configuré** : staleTime et cacheTime adaptés à chaque type de données

---

## 🔗 Mapping Hooks ↔ Widgets

| Hook | Widget(s) | Endpoint | Cache Time |
|------|-----------|----------|------------|
| `useDashboardKPIs` | MetricCard, StatsGrid | `/api/dashboard/kpis` | 5-10 min |
| `useCorrelationMatrix` | CorrelationHeatmap | `/api/correlations/matrix` | 15-30 min |
| `useCorrelationNetwork` | CorrelationNetwork | `/api/correlations/network` | 15-30 min |
| `useSectorAllocation` | SectorWheel, TreemapChart | `/api/stocks/sectors` | 30-60 min |
| `useEfficientFrontier` | EfficientFrontier | `/api/backtests/efficient_frontier` | 1-2 hours |
| `useCapitalFlows` | SankeyDiagram | `/api/flows/capital` | 15-30 min |
| `useOrderBook` | OrderBook | `/api/orderbook?ticker=...` | 30 sec - 2 min |

---

## 🚀 Prochaines Étapes

### Intégration dans les Pages

1. **Dashboard** (`/dashboard`):
   ```tsx
   import { useDashboardKPIs } from '@/hooks/useDashboardKPIs';
   // Utiliser avec MetricCard, StatsGrid
   ```

2. **Diagnostics** (`/diagnostics`):
   ```tsx
   import { useCorrelationNetwork } from '@/hooks/useCorrelationNetwork';
   // Utiliser avec CorrelationNetwork, CorrelationHeatmap
   ```

3. **Portfolio** (`/portfolios`):
   ```tsx
   import { useSectorAllocation, useEfficientFrontier } from '@/hooks/...';
   // Utiliser avec SectorWheel, TreemapChart, EfficientFrontier
   ```

4. **Analytics** (`/analytics`):
   ```tsx
   import { useCapitalFlows } from '@/hooks/useCapitalFlows';
   // Utiliser avec SankeyDiagram
   ```

5. **Trading** (`/trading`):
   ```tsx
   import { useOrderBook } from '@/hooks/useOrderBook';
   // Utiliser avec OrderBook
   ```

---

## ✅ Checklist

- [x] 6 hooks créés avec TypeScript
- [x] Interfaces typées pour toutes les données
- [x] Gestion d'erreurs avec fallback
- [x] Cache configuré selon le type de données
- [x] Documentation créée
- [ ] Intégration dans les pages (à faire)
- [ ] Tests des hooks (à faire)

---

## 📝 Notes

- Tous les hooks utilisent `apiGet` de `@/api/client`
- Gestion automatique du format `{ok, data}` du backend
- Fallback structures garantissent que l'UI ne crash jamais
- Cache times adaptés à la fréquence de mise à jour des données
- OrderBook a un auto-refetch pour feeling temps réel

---

## 🔗 Références

- `PIPELINES_CREATED.md` - Pipelines backend correspondants
- `MASTER_VISUALIZATION_TEMPLATES.md` - Widgets de visualisation
- `copilot-app/frontend/webapp/src/hooks/useForecasts.ts` - Exemple de hook existant

