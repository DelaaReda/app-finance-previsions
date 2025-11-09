# ARCHITECTURE ANALYSIS TASKS - Detailed Implementation Plan

Based on the comprehensive architecture analysis provided on 2025-11-09, here are the detailed tasks to improve the Finance Copilot system.

## 🔧 PRIORITY IMPROVEMENTS TO IMPLEMENT

### 1. AGENT ORGANIZATION & ORCHESTRATION
- **Split agent responsibilities**: Separate ingestion agents, forecasting agents, and aggregation/evaluation agents
- **Centralize scheduling**: Implement unified scheduler (APScheduler) that orchestrates agents: ingestion → forecasting → aggregation → quality checks
- **Add consistent logging**: Each agent should write to a log file in `logs/` with run status, timing, and metadata
- **Implement fallback logic for g4f**: Centralize g4f query logic with retry mechanism and graceful fallbacks

### 2. BACKEND OPTIMIZATIONS
- **Pre-compute brief data**: Create `brief_agent.py` that generates daily market summary (top 3 signals/risks) saved to `data/brief/dt=YYYYMMDD/daily.json`
- **Add backend caching**: Implement in-memory caching for frequently accessed endpoints to avoid repeated disk reads
- **Optimize response sizes**: Implement pagination/filtering for large datasets (e.g., limit forecasts returned per request)
- **Remove dead code**: Clean up legacy Dash/Streamlit code now that React frontend is the primary UI
- **Factor common utilities**: Consolidate duplicate functions like `_latest_dt_under()` into shared modules

### 3. FRONTEND PERFORMANCE
- **Implement route-level code splitting**: Ensure each page (Dashboard, Forecasts, LLMJudge, etc.) is lazy-loaded
- **Add component-level lazy loading**: Dynamically load heavy components (charts, complex filters)
- **Optimize bundle splitting**: Use Vite's bundle splitting for chart libraries and other heavy dependencies
- **Global state management**: Create Context providers for watchlist, user settings, and other shared data
- **Enhance user feedback**: Add better loading indicators and progress feedback for LLM operations

### 4. G4F INTEGRATION STABILITY
- **Centralize g4f calls**: Create utility module `llm_utils.py` with standardized `query_g4f(prompt, model)` function
- **Implement model fallbacks**: Try multiple g4f models if primary one fails
- **Context sharing**: Pre-calculate common contexts to avoid redundant processing
- **Rate limiting**: Add throttling to prevent excessive API usage

### 5. DATA PIPELINE IMPROVEMENTS
- **Standardize data formats**: Ensure all agent outputs use consistent formats (Parquet for structured data, JSON for config)
- **Add data quality checks**: Validate data integrity before writing to storage
- **Update frequency documentation**: Document the intended refresh frequency for each data type
- **Implement data monitoring**: Track data freshness and alert on staleness

## 📊 CURRENT STATE ASSESSMENT

Based on the original requirements and what has been accomplished:

### ✅ COMPLETED SUCCESSFULLY
- Forecast pipeline is generating real data for 8 tickers (SPY, QQQ, AAPL, MSFT, TSLA, NVDA, GOOGL, META)
- ML + G4F hybrid system is operational
- Data is being saved to persistent storage in `data/forecasts.json`
- Endpoints are returning real data instead of empty responses

### ⚠️ AREAS REQUIRING ATTENTION
- API endpoint filtering may need adjustment for Query parameter handling
- Agent orchestration could be improved with centralized scheduling
- Frontend code splitting and lazy loading needs to be extended
- G4F integration should be made more robust with centralized utilities

## 🎯 NEXT PHASE PRIORITIES

1. **High Priority**: Implement the centralized g4f utility and fallback mechanisms
2. **Medium Priority**: Enhance agent scheduling and logging
3. **Low Priority**: Frontend performance optimizations and bundle splitting
4. **Continuous**: Data quality monitoring and pipeline documentation

This architecture analysis reveals a mature system that needs refinement rather than rebuild. The core functionality is working well, but improvements in orchestration, caching, and frontend performance will significantly enhance the user experience.