# API-PORTFOLIO-004 : Performance Charts Frontend - Plan

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-07  
**Mission** : Beautiful performance charts to visualize portfolio analytics  
**Points estimés** : +80  
**Priorité** : 🔥 HIGH (complete the portfolio feature with visual insights)

---

## 🎯 Objectif

Create stunning performance visualization:
- ✅ Equity Curve chart (portfolio vs benchmark)
- ✅ Drawdown chart (underwater periods)
- ✅ Performance metrics cards
- ✅ Benchmark comparison table
- ✅ Date range selector (1M, 3M, YTD, 1Y, All)
- ✅ Benchmark selector (SPY, QQQ, IWM, AGG)

---

## 🏗️ Architecture Frontend

### Components Structure

```
components/
├── portfolios/
│   ├── PerformanceCharts.tsx (NEW, ~200 lines)
│   │   - Main orchestrator component
│   │   - Date range & benchmark selectors
│   │   - Grid layout for charts
│   │
│   ├── EquityCurveChart.tsx (NEW, ~150 lines)
│   │   - Line chart (Recharts)
│   │   - Portfolio vs Benchmark lines
│   │   - Tooltips, legends
│   │
│   ├── DrawdownChart.tsx (NEW, ~120 lines)
│   │   - Area chart (Recharts)
│   │   - Red negative area
│   │   - Max drawdown marker
│   │
│   ├── MetricsCards.tsx (NEW, ~150 lines)
│   │   - Grid of metric cards
│   │   - 8 performance metrics
│   │   - Color-coded (green/red)
│   │
│   └── BenchmarkComparisonTable.tsx (NEW, ~100 lines)
│       - Table with 6 comparison metrics
│       - Badges for outperformance

hooks/
├── usePortfolioPerformance.ts (ENHANCE)
│   - Add usePortfolioTimeseries() hook
│   - Fetch time series data for charts

widgets/
└── PortfolioManagerWidget.tsx (MODIFY)
    - Add "View Performance" button on cards
    - Open modal with PerformanceCharts
```

---

## 📊 Charts Specifications

### 1. Equity Curve Chart

**Chart Type** : Line chart (Recharts `LineChart`)

**Data** :
- X-axis : Dates
- Y-axis : Normalized value (starts at 100)
- Lines : Portfolio (blue), Benchmark (gray)

**Features** :
- ✅ Tooltips on hover (date, portfolio value, benchmark value, diff)
- ✅ Legend (Portfolio, Benchmark)
- ✅ Grid lines
- ✅ Responsive
- ✅ Color: Blue for portfolio, Gray for benchmark
- ✅ Highlight outperformance areas (green fill between lines when portfolio > benchmark)

**Example** :
```
Portfolio Value
120 ┤     ╭─Portfolio─╮
110 ┤   ╭─╯           ╰─
100 ┼───╯ Benchmark ────
 90 ┤
    └──────────────────→ Time
   Jan  Mar  May  Jul  Sep
```

---

### 2. Drawdown Chart

**Chart Type** : Area chart (Recharts `AreaChart`)

**Data** :
- X-axis : Dates
- Y-axis : Drawdown (%)
- Area : Red negative area below 0%

**Features** :
- ✅ Red gradient fill (underwater periods)
- ✅ Marker for max drawdown point
- ✅ Tooltips (date, drawdown %)
- ✅ 0% reference line
- ✅ Grid lines

**Example** :
```
Drawdown (%)
  0% ┼─────────────────
 -5% ┤     ╭╮
-10% ┤   ╭╯╰╮
-15% ┤  ╭╯  ╰╮  ← Max: -18.5%
-20% ┤ ╭╯    ╰╮
    └──────────────────→ Time
```

---

### 3. Metrics Cards

**Layout** : Grid (4 columns × 2 rows = 8 cards)

**Card Structure** :
```
┌─────────────────────┐
│ Total Return        │
│ +28.7%         ↑    │ ← Green if positive
└─────────────────────┘
```

**8 Metrics** :
1. Total Return (%)
2. Annualized Return (%)
3. Volatility (%)
4. Sharpe Ratio
5. Max Drawdown (%)
6. Win Rate (%)
7. Best Day (%)
8. Worst Day (%)

**Color Coding** :
- Green : Positive values, high Sharpe, low volatility
- Red : Negative values, high drawdown
- Blue : Neutral metrics

---

### 4. Benchmark Comparison Table

**Layout** : Simple table (2 columns)

| Metric | Value |
|--------|-------|
| Portfolio Return | +28.7% |
| Benchmark Return | +24.1% |
| Outperformance | +4.6% 🟢 |
| Correlation | 0.84 |
| Beta | 1.15 |
| Alpha | +1.8% 🟢 |

**Features** :
- ✅ Badges for positive/negative values
- ✅ Icons for outperformance (🟢 beat, 🔴 underperform)
- ✅ Tooltips explaining each metric

---

## 🎯 User Flow

### View Performance Flow

1. User sees portfolio card in `PortfolioManagerWidget`
2. Clicks "📊 View Performance" button
3. Modal opens with `PerformanceCharts` component
4. Sees:
   - Date range selector (1M, 3M, YTD, 1Y, All)
   - Benchmark selector (SPY, QQQ, IWM, AGG)
   - Equity curve chart (portfolio vs benchmark)
   - Drawdown chart
   - 8 metrics cards
   - Benchmark comparison table
5. Can change date range → charts update
6. Can change benchmark → comparison updates
7. Can close modal or navigate away

---

## 🎨 UI Design

### Modal Layout

```
┌─────────────────────────────────────────────────┐
│ Tech Giants - Performance                   [×] │
├─────────────────────────────────────────────────┤
│ [1M] [3M] [YTD] [1Y] [All]    Benchmark: [SPY▼] │
├─────────────────────────────────────────────────┤
│                                                 │
│  Equity Curve Chart                             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  Drawdown Chart                                 │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                │
│                                                 │
├─────────────────────────────────────────────────┤
│  [Total Return] [Ann. Return] [Volatility] [...] │
│  [Sharpe]       [Drawdown]    [Win Rate]   [...] │
├─────────────────────────────────────────────────┤
│  Benchmark Comparison                           │
│  Portfolio: +28.7% vs SPY: +24.1% (+4.6% 🟢)    │
│  Beta: 1.15 | Alpha: +1.8% | Corr: 0.84         │
└─────────────────────────────────────────────────┘
```

---

## 📊 Technical Implementation

### React Query Hook

```typescript
function usePortfolioTimeseries(
  portfolioId: string | null,
  benchmark: string = 'SPY',
  startDate?: string,
  endDate?: string
) {
  return useQuery({
    queryKey: qk.portfolioPerformance(portfolioId, benchmark, startDate, endDate),
    queryFn: () => fetchPortfolioTimeseries(portfolioId!, benchmark, startDate, endDate),
    enabled: !!portfolioId,
    staleTime: 60 * 60 * 1000, // 1 hour
    retry: 2
  })
}
```

### Recharts Implementation

```typescript
<LineChart data={data}>
  <CartesianGrid strokeDasharray="3 3" />
  <XAxis dataKey="date" />
  <YAxis />
  <Tooltip />
  <Legend />
  <Line 
    type="monotone" 
    dataKey="portfolio" 
    stroke="#2196F3" 
    strokeWidth={2}
    name="Portfolio"
  />
  <Line 
    type="monotone" 
    dataKey="benchmark" 
    stroke="#9E9E9E" 
    strokeWidth={2}
    name={benchmark}
  />
</LineChart>
```

### Date Range Calculation

```typescript
const DATE_RANGES = {
  '1M': () => subMonths(new Date(), 1),
  '3M': () => subMonths(new Date(), 3),
  'YTD': () => startOfYear(new Date()),
  '1Y': () => subYears(new Date(), 1),
  'All': () => subYears(new Date(), 10) // Max 10 years
}
```

---

## 🎯 Features

### Date Range Selector
- Buttons: 1M, 3M, YTD, 1Y, All
- Active state highlighting
- Updates charts on click

### Benchmark Selector
- Dropdown: SPY, QQQ, IWM, AGG, Custom
- Updates comparison metrics
- Updates benchmark line in equity curve

### Responsive Design
- Desktop: Side-by-side charts
- Mobile: Stacked charts
- Charts resize automatically

### Loading States
- Skeleton loaders for charts
- "Calculating..." message
- Smooth transitions

### Empty States
- "No data available for this period"
- "Add tickers to see performance"
- Helpful messages

---

## 📈 Example Data Flow

1. User clicks "View Performance" on Tech Giants portfolio
2. `PerformanceCharts` component renders
3. `usePortfolioTimeseries(portfolioId, 'SPY', startDate, endDate)` fetches data
4. Backend calls `/api/portfolios/{id}/performance/timeseries?benchmark=SPY`
5. Receives:
   ```json
   {
     "portfolio": {
       "dates": ["2024-01-01", ...],
       "equity_curve": [100, 101.5, ...],
       "drawdown": [0, -0.5, ...]
     },
     "benchmark": {...},
     "metrics": {...},
     "comparison": {...}
   }
   ```
6. Charts render with data
7. User changes to "QQQ" benchmark
8. Hook refetches with QQQ
9. Charts update smoothly

---

## 🎯 Timeline

**Estimation** : 2-3h

- `usePortfolioTimeseries` hook : 30min
- `EquityCurveChart` component : 45min
- `DrawdownChart` component : 30min
- `MetricsCards` component : 30min
- `BenchmarkComparisonTable` component : 20min
- `PerformanceCharts` orchestrator : 30min
- Integration in `PortfolioManagerWidget` : 15min
- Testing : 20min

**Start** : NOW

---

## 📊 Impact

### User Value
- 📊 **Visual insights** : See performance at a glance
- 📈 **Equity curve** : Track portfolio growth vs benchmark
- 🔴 **Drawdown** : Identify risky periods
- 🎯 **Metrics cards** : Key stats in one view
- 💡 **Benchmark beating** : Visual confirmation of outperformance
- ⚡ **Interactive** : Change date range & benchmark instantly

### Technical
- ✅ **Recharts** : Beautiful, responsive charts
- ✅ **React Query** : Efficient data fetching & caching
- ✅ **Mantine UI** : Consistent design system
- ✅ **Professional** : Hedge fund grade visualization
- ✅ **Extensible** : Ready for monthly heatmap, returns distribution

---

**Signé** : ELENA-39  
**Status** : Starting implementation
