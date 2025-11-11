# API-PORTFOLIO-003 : Performance Analytics Phase 2 - Plan

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-07  
**Mission** : Real portfolio performance calculation with metrics & charts  
**Points estimés** : +100  
**Priorité** : 🔥 HIGH (complete the portfolio feature with real analytics)

---

## 🎯 Objectif

Implémenter les vraies métriques de performance pour les portfolios :
- ✅ Fetch historical price data (yfinance)
- ✅ Calculate returns, volatility, Sharpe ratio
- ✅ Benchmark comparison (SPY, QQQ, etc.)
- ✅ Drawdown analysis
- ✅ Performance charts (equity curve, monthly returns)

---

## 🏗️ Architecture

### Backend Service Enhancement

**File** : `backend/services/portfolio_performance_service.py` (NEW)

**Core Functions** :
```python
def fetch_price_data(tickers: List[str], start_date: str, end_date: str)
  → pd.DataFrame

def calculate_returns(prices: pd.DataFrame)
  → pd.DataFrame

def calculate_portfolio_metrics(returns: pd.DataFrame, weights: Dict[str, float])
  → PortfolioMetrics

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02)
  → float

def calculate_drawdown(equity_curve: pd.Series)
  → pd.Series, float (drawdown series, max drawdown)

def compare_to_benchmark(portfolio_returns: pd.Series, benchmark_returns: pd.Series)
  → BenchmarkComparison
```

**Data Models** :
```python
class PortfolioMetrics(BaseModel):
    total_return: float
    annualized_return: float
    volatility: float  # annualized
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float  # % positive days
    best_day: float
    worst_day: float
    
class BenchmarkComparison(BaseModel):
    benchmark_ticker: str
    portfolio_return: float
    benchmark_return: float
    outperformance: float  # portfolio - benchmark
    correlation: float
    beta: float  # portfolio beta vs benchmark
    alpha: float  # portfolio alpha vs benchmark
    
class PerformanceTimeSeries(BaseModel):
    dates: List[str]
    equity_curve: List[float]
    drawdown: List[float]
    returns: List[float]
```

---

### Modified Backend Service

**File** : `backend/services/portfolio_service.py` (MODIFY)

Update `get_performance()` method to use real calculations instead of placeholder.

---

### API Enhancement

**File** : `backend/api/routes/portfolios.py` (MODIFY)

Add new endpoint:
```python
@router.get("/portfolios/{id}/performance/timeseries")
def get_portfolio_performance_timeseries(
    id: str,
    start_date: str = Query(None),
    end_date: str = Query(None)
) -> PerformanceTimeSeries
```

---

### Frontend Components

**Files** :
- `hooks/usePortfolioPerformance.ts` (ENHANCE with timeseries hook)
- `components/portfolios/PerformanceCharts.tsx` (NEW)
- `components/portfolios/MetricsCard.tsx` (NEW)
- `components/portfolios/BenchmarkComparison.tsx` (NEW)

---

## 📊 Features

### 1. Real Performance Calculation

**Metrics** :
- ✅ Total return (%)
- ✅ Annualized return (%)
- ✅ Volatility (annualized std dev)
- ✅ Sharpe ratio (return / volatility, adjusted for risk-free rate)
- ✅ Max drawdown (%)
- ✅ Win rate (% positive days)
- ✅ Best/worst day

**Data Source** :
- yfinance for historical prices
- Daily close prices
- Adjusts for splits/dividends

---

### 2. Benchmark Comparison

**Benchmarks** :
- SPY (S&P 500) - default
- QQQ (Nasdaq 100)
- IWM (Russell 2000)
- AGG (Bonds)
- Custom ticker

**Comparison Metrics** :
- ✅ Outperformance (portfolio return - benchmark return)
- ✅ Correlation (how closely portfolio tracks benchmark)
- ✅ Beta (portfolio volatility vs benchmark)
- ✅ Alpha (excess return vs benchmark, risk-adjusted)

---

### 3. Performance Charts

**Chart Types** :

1. **Equity Curve** (Line chart)
   - X-axis: Time
   - Y-axis: Portfolio value (normalized to 100)
   - Multiple lines: Portfolio + Benchmark(s)
   - Shows growth over time

2. **Drawdown Chart** (Area chart)
   - X-axis: Time
   - Y-axis: Drawdown (%)
   - Red area showing underwater periods
   - Highlights max drawdown point

3. **Monthly Returns Heatmap** (Calendar heatmap)
   - Rows: Years
   - Columns: Months
   - Color: Green (positive) to Red (negative)
   - Quick visual of performance patterns

4. **Returns Distribution** (Histogram)
   - X-axis: Return buckets
   - Y-axis: Frequency
   - Shows distribution of daily/monthly returns

---

## 🎯 User Flows

### View Performance Metrics Flow
1. User navigates to portfolio card
2. Clicks "View Performance" button
3. Modal/page opens with performance dashboard
4. Sees metrics (Sharpe, returns, drawdown)
5. Sees equity curve chart (portfolio vs SPY)
6. Can change date range (1M, 3M, YTD, 1Y, All)
7. Can change benchmark (SPY, QQQ, etc.)

### Compare Portfolios Flow
1. User selects 2+ portfolios
2. Clicks "Compare" button
3. Side-by-side comparison view
4. Shows metrics table
5. Shows overlaid equity curves
6. Highlights best performer (green badge)

---

## 🧪 Technical Implementation

### Calculation Logic

**Equal-weighted portfolio** (Phase 2):
- Each ticker gets equal weight (1/N)
- Portfolio return = average of ticker returns
- Simple but effective baseline

**Custom weights** (Future Phase 3):
- User can specify % allocation per ticker
- Portfolio return = weighted sum of returns

### Data Fetching Strategy

**Caching** :
- Cache price data for 1 hour (prices don't change frequently)
- Cache performance metrics for 30 minutes
- Invalidate on portfolio tickers change

**Date Ranges** :
- Default: 1 year
- Options: 1M, 3M, 6M, YTD, 1Y, 2Y, 5Y, All
- Max range: 10 years (performance reasons)

**Error Handling** :
- Missing tickers: Skip and warn
- Insufficient data: Return null with message
- API failures: Fallback to cached data

---

## 📈 Example Output

### Performance Metrics
```json
{
  "portfolio_id": "uuid-123",
  "portfolio_name": "Tech Giants",
  "period": "1Y",
  "total_return": 0.287,          // 28.7%
  "annualized_return": 0.287,
  "volatility": 0.312,            // 31.2%
  "sharpe_ratio": 0.92,
  "max_drawdown": -0.185,         // -18.5%
  "win_rate": 0.537,              // 53.7% positive days
  "best_day": 0.087,              // +8.7%
  "worst_day": -0.062,            // -6.2%
  "benchmark": {
    "ticker": "SPY",
    "portfolio_return": 0.287,
    "benchmark_return": 0.241,
    "outperformance": 0.046,      // +4.6% vs SPY
    "correlation": 0.84,
    "beta": 1.15,
    "alpha": 0.018                // +1.8% alpha
  }
}
```

---

## 🎯 Timeline

**Estimation** : 3-4h

- Backend service (yfinance + calculations) : 1.5h
- API endpoints : 30min
- Frontend hooks : 30min
- Performance charts (Recharts) : 1h
- Testing : 30min

**Start** : NOW

---

## 📊 Impact

### User Value
- 📈 **Data-driven decisions** : Know which portfolios perform best
- 🎯 **Risk awareness** : See volatility, drawdown, Sharpe ratio
- 💡 **Benchmark comparison** : Beat the market or not?
- 📊 **Visual insights** : Charts tell the story
- ⚡ **Fast** : Cached calculations, instant display

### Technical
- ✅ **Real calculations** : No more placeholders
- ✅ **yfinance integration** : Industry-standard data source
- ✅ **Quantitative metrics** : Professional-grade analytics
- ✅ **Extensible** : Ready for advanced features (optimization, rebalancing)

---

**Signé** : ELENA-39  
**Status** : Starting implementation
