# 🎨 MASTER - Tous les Templates de Visualisation

**Date**: 2025-01-27  
**Agent**: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77  
**Total** : **22 templates** de visualisation professionnels !

---

## 📊 Vue d'Ensemble

| Phase | Templates | Description |
|-------|-----------|-------------|
| **Base** | 4 | Fondations (MetricCard, StatsGrid, ComparisonChart, ProgressRing) |
| **Avancé** | 8 | Avancés (CorrelationHeatmap, PerformanceGauge, etc.) |
| **ULTRA** | 5 | Trading technique (Candlestick, VolumeProfile, etc.) |
| **MASTER** | 5 | **Innovation (OrderBook, EfficientFrontier, CorrelationNetwork, Treemap, Sankey)** |

**Total** : **22 templates** ! 🎨🔥🚀

---

## 🚀 5 Nouveaux Templates MASTER

### 1. **OrderBook** 📖

**Usage** : Visualisation du carnet d'ordres (bid/ask)

```tsx
<OrderBook
  title="Carnet d'Ordres - AAPL"
  bids={[
    { price: 150.00, quantity: 1000 },
    { price: 149.99, quantity: 500 },
  ]}
  asks={[
    { price: 150.01, quantity: 800 },
    { price: 150.02, quantity: 1200 },
  ]}
  lastPrice={150.00}
/>
```

**Features** :
- ✅ Bids (achats) en teal, Asks (ventes) en red
- ✅ Quantités normalisées visuellement
- ✅ Spread calculé automatiquement
- ✅ Tooltips avec prix + quantité
- ✅ Style Bloomberg Terminal

**Cas d'usage** : Trading en direct, analyse de liquidité, market depth

---

### 2. **EfficientFrontier** 📈

**Usage** : Frontière efficiente (Portfolio Optimization - MPT)

```tsx
<EfficientFrontier
  title="Frontière Efficiente"
  frontier={[
    { risk: 10, return: 8, sharpe: 0.8 },
    { risk: 15, return: 12, sharpe: 0.9 },
  ]}
  portfolios={[
    { name: 'Portfolio A', risk: 12, return: 10, color: '#f59e0b' },
  ]}
/>
```

**Features** :
- ✅ Courbe de frontière efficiente
- ✅ Overlay de portfolios existants
- ✅ Calcul automatique des stats
- ✅ Tooltips avec risque/rendement/Sharpe

**Cas d'usage** : Portfolio optimization, Modern Portfolio Theory, allocation optimale

---

### 3. **CorrelationNetwork** 🕸️

**Usage** : Graph network de corrélations interactif

```tsx
<CorrelationNetwork
  title="Réseau de Corrélations"
  nodes={[
    { id: 'AAPL', label: 'Apple', sector: 'Tech' },
    { id: 'MSFT', label: 'Microsoft', sector: 'Tech' },
  ]}
  links={[
    { source: 'AAPL', target: 'MSFT', correlation: 0.85 },
  ]}
  threshold={0.5}
/>
```

**Features** :
- ✅ Graph network interactif
- ✅ Nodes positionnés en cercle
- ✅ Liens colorés selon corrélation
- ✅ Sélection de nodes (click)
- ✅ Tooltips avec détails

**Cas d'usage** : Analyse de corrélations, diversification, cluster analysis

---

### 4. **TreemapChart** 🌳

**Usage** : Treemap pour allocation hiérarchique

```tsx
<TreemapChart
  title="Allocation Portfolio"
  data={[
    { id: 'tech', label: 'Technology', value: 35, color: '#3b82f6' },
    { id: 'finance', label: 'Finance', value: 25, color: '#10b981' },
  ]}
  size={600}
/>
```

**Features** :
- ✅ Treemap avec tailles proportionnelles
- ✅ Couleurs personnalisables
- ✅ Tooltips avec métadonnées
- ✅ Hover effects (scale)
- ✅ Layout optimisé

**Cas d'usage** : Allocation portfolio, répartition par secteur, hiérarchie de valeurs

---

### 5. **SankeyDiagram** 🌊

**Usage** : Diagramme Sankey pour flux

```tsx
<SankeyDiagram
  title="Flux de Capitaux"
  nodes={[
    { id: 'source1', label: 'Source A', color: '#3b82f6' },
    { id: 'target1', label: 'Target X', color: '#10b981' },
  ]}
  links={[
    { source: 'source1', target: 'target1', value: 1000000, color: '#3b82f6' },
  ]}
  height={400}
/>
```

**Features** :
- ✅ Diagramme de flux Sankey
- ✅ Nodes positionnés automatiquement
- ✅ Liens avec largeurs proportionnelles
- ✅ Tooltips avec valeurs
- ✅ Support multi-colonnes

**Cas d'usage** : Flux de capitaux, allocation de budget, transitions, transformations

---

## 🔗 Mapping Data ↔ Widgets

| Widget | Endpoint/API | Service/Job à vérifier | Dataset persistant |
|--------|--------------|------------------------|--------------------|
| MetricCard / StatsGrid | `/api/dashboard/kpis` | `src/services/dashboard_service.py` + `jobs/dashboard_refresh.py` | `copilot-app/backend/data/dashboard/kpis.json` |
| ComparisonChart / RiskMatrix / PerformanceGauge | `/api/forecasts`, `/api/backtests/metrics` | `services/forecasts_service.py`, `jobs/backtests_runner.py` | `data/forecasts/*.json`, `data/backtests/metrics.json` |
| CandlestickChart / VolumeProfile | `/api/stocks/prices?ticker=...` | `services/stocks_service.py`, `jobs/market_data_ingest.py` | `data/stocks/prices/<ticker>.json` |
| SectorWheel / TreemapChart | `/api/stocks/sectors`, `/api/stocks/weights` | `jobs/sector_allocation.py`, `services/portfolio_service.py` | `data/stocks/sectors.json`, `data/portfolio/weights.json` |
| OrderBook | `/api/orderbook?ticker=...` (à exposer) | `jobs/orderbook_ingest.py` (temps réel), `services/market_microstructure.py` | `data/market/orderbook_<ticker>.json` |
| EfficientFrontier | `/api/backtests/efficient_frontier` | `jobs/backtests_optimizer.py`, `services/backtests_service.py` | `data/backtests/efficient_frontier.json` |
| CorrelationNetwork / CorrelationHeatmap | `/api/correlations/network`, `/api/correlations/matrix` | `jobs/correlation_calculator.py`, `services/correlation_service.py` | `data/correlations/matrix.json` |
| SankeyDiagram | `/api/flows/capital` | `jobs/capital_flow.py`, `services/flows_service.py` | `data/flows/capital.json` |
| TimelineEvents / HeatmapCalendar | `/api/news/events`, `/api/calendar` | `jobs/calendar_ingest.py`, `services/news_service.py` | `data/calendar/events.json`, `data/news/events.json` |

> 🧷 Avant de brancher un widget, vérifiez que l’endpoint renvoie `generated_at`, un tableau non vide, et les champs requis par le composant. Aucun mock n’est accepté.

---

## 🧪 Exemple d’intégration complète — CorrelationNetwork

1. **Générer la donnée**
   ```bash
   source copilot-app/backend/.venv/bin/activate
   python copilot-app/backend/jobs/correlation_calculator.py --tickers "AAPL,MSFT,NVDA,QQQ,SPY" --force
   jq '.' copilot-app/backend/data/correlations/matrix.json | head -40
   ```

2. **Service + route**
   ```python
   # services/correlation_service.py
   from storage import io

   def get_network(threshold: float = 0.5):
       payload = io.load_json("correlations/matrix") or {}
       # transformer matrix -> nodes/links ...
       return {"nodes": nodes, "links": links}
   ```
   ```python
   # api/main.py
   @app.get("/api/correlations/network")
   async def correlations_network(threshold: float = 0.5):
       data = get_network(threshold=threshold)
       return _ok({"data": data, "generated_at": datetime.utcnow().isoformat()})
   ```

3. **Hook frontend**
   ```ts
   export const useCorrelationNetwork = (threshold = 0.5) =>
     useQuery({
       queryKey: ['cor-network', threshold],
       queryFn: async () => {
         const res = await api.fetchJson('/api/correlations/network', { searchParams: { threshold } });
         return res?.data ?? { nodes: [], links: [] };
       },
     });
   ```

4. **Widget dans la page**
   ```tsx
   import { CorrelationNetwork } from '@/components/visualizations';
   import { useCorrelationNetwork } from '@/hooks/useCorrelations';

   const Diagnostics = () => {
     const { data, isLoading } = useCorrelationNetwork(0.6);
     if (isLoading) return <Skeleton height={420} radius="lg" />;
     return (
       <CorrelationNetwork
         title="Réseau de corrélations (≥ 0.6)"
         nodes={data.nodes}
         links={data.links}
         threshold={0.6}
       />
     );
   };
   ```

5. **Preuve**
   ```bash
   mkdir -p proofs/UI-AUDIT-$(date +%Y%m%d)
   curl -s "http://localhost:8050/api/correlations/network?threshold=0.6" | jq '.' > proofs/.../cor-network-after.json
   # capture UI via tests/finance_app_test-v2.html → proofs/.../cor-network-after.png
   ```
   Mettre à jour `SCORE_AGENTS.md` (mission, points, référence aux preuves).

---

## ✅ Checklist de livraison

- [ ] Dataset réel généré via `jobs/*.py` et stocké dans `data/...`.
- [ ] Endpoint expose `generated_at`, `data`, `count` (ou équivalent).
- [ ] Hook gère `loading`, `error`, `empty`.
- [ ] Widget affiche contexte (titre, tickers, dernière mise à jour).
- [ ] Preuve déposée (screenshot + JSON + scoreboard).

**Rappels**
- Si un widget requiert une donnée inexistante, implémentez d’abord le pipeline (job + service + dataset).
- Utilisez `storage.io` pour persister, `finance-copilot.sh restart` pour relancer la stack, et suivez `copilot-app/INVESTIGATION_GUIDE.md` pour l’investigation complète.
