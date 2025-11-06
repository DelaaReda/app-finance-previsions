# API-PORTFOLIO-001 : Portfolio/Watchlist Management - Plan

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Complete portfolio/watchlist management system  
**Points estimés** : +80  
**Priorité** : 🔥 HIGH (most requested feature)

---

## 🎯 Objectif

Créer un système complet de gestion de portefeuilles/watchlists :
- ✅ Créer des watchlists personnalisées
- ✅ Ajouter/retirer des tickers
- ✅ Suivre la performance
- ✅ Comparer vs benchmark
- ✅ Gérer plusieurs watchlists

---

## 🏗️ Architecture

### Backend Service

**File** : `backend/services/portfolio_service.py`

**Data Models** :
```python
class Portfolio(BaseModel):
    id: str
    name: str
    description: str
    tickers: List[str]
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

class PortfolioPerformance(BaseModel):
    portfolio_id: str
    total_return: float
    avg_return: float
    volatility: float
    sharpe_ratio: float
    vs_benchmark: Dict[str, float]
```

**Methods** :
- `create_portfolio(name, description, tickers)`
- `get_portfolio(id)`
- `list_portfolios()`
- `update_portfolio(id, ...)`
- `delete_portfolio(id)`
- `add_tickers(id, tickers)`
- `remove_tickers(id, tickers)`
- `get_performance(id, benchmark)`

**Storage** : JSON file (`data/user_portfolios.json`)

---

### API Endpoints

**8 endpoints** :

1. `POST /api/portfolios` - Create portfolio
2. `GET /api/portfolios` - List portfolios
3. `GET /api/portfolios/{id}` - Get portfolio
4. `PUT /api/portfolios/{id}` - Update portfolio
5. `DELETE /api/portfolios/{id}` - Delete portfolio
6. `POST /api/portfolios/{id}/tickers` - Add tickers
7. `DELETE /api/portfolios/{id}/tickers/{ticker}` - Remove ticker
8. `GET /api/portfolios/{id}/performance` - Get performance

---

## 📊 Use Cases

### 1. Tech Watchlist
```json
{
  "name": "Tech Giants",
  "description": "FAANG stocks",
  "tickers": ["AAPL", "MSFT", "GOOGL", "META", "AMZN"]
}
```

### 2. Defensive Portfolio
```json
{
  "name": "Safe Haven",
  "description": "Low volatility defensive",
  "tickers": ["JNJ", "PG", "KO", "TLT", "GLD"]
}
```

### 3. Performance Tracking
Track portfolio vs SPY benchmark, get Sharpe ratio, volatility, returns

---

## 🎯 Timeline

**Estimation** : 2-3h

- Data models : 30min
- Service methods : 1h
- API endpoints : 45min
- Testing : 30min

**Start** : NOW

---

**Signé** : ELENA-39  
**Status** : Starting implementation
