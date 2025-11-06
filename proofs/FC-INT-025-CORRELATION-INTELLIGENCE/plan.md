# FC-INT-025 : Correlation Intelligence - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Service + Widget de corrélations intelligentes avec explications LLM  
**Points estimés** : +80

---

## 🎯 Objectif

Créer le **Correlation Intelligence** - Système qui calcule les corrélations entre assets et utilise LLM pour expliquer **pourquoi** ces corrélations existent et **comment** les exploiter.

---

## 🧠 Vision

**Problème** : Les corrélations traditionnelles montrent des chiffres (-1 à +1) mais n'expliquent pas **pourquoi** ni **quoi faire**.

**Solution** : Combiner analyse quantitative + LLM pour :
- Calculer corrélations
- Identifier patterns cachés
- Expliquer les drivers (LLM)
- Suggérer actions (hedging, diversification, arbitrage)

---

## 📊 Architecture

### Backend Service

```python
CorrelationIntelligenceService
├── calculate_correlations(universe, window)
│   └── Returns correlation matrix
├── identify_interesting_pairs(correlations, threshold)
│   └── Finds strong correlations (>0.7 or <-0.3)
├── analyze_with_llm(pair, correlation, context)
│   └── LLM explains WHY + suggests HOW
└── generate_correlation_intelligence()
    └── Full analysis with actionable insights
```

### Frontend Widget

```tsx
CorrelationIntelligenceWidget
├── CorrelationMatrix (heatmap visual)
├── TopCorrelationsPairs (list)
├── CorrelationExplanationCard (LLM insights)
└── ActionableInsights (what to do)
```

---

## 🔧 Implementation

### 1. Backend Service (400 lines)

**Path** : `backend/services/correlation_intelligence_service.py`

**Methods** :
- `calculate_correlation_matrix(tickers, window='30d')` - Pandas corr()
- `identify_interesting_pairs(matrix, threshold)` - Filter strong correlations
- `_analyze_correlation_with_llm(ticker1, ticker2, corr, context)` - LLM explanation
- `generate_correlation_intelligence(universe)` - Main entry point

**LLM Prompt** (example) :
```
You are analyzing asset correlations.

Pair: AAPL & MSFT
Correlation: +0.85 (strong positive)
Market context: BULL_MARKET

Explain:
1. WHY do these assets correlate? (2-3 sentences)
2. What drives this correlation? (sector, macro, etc.)
3. Trading implications (hedging, diversification, arbitrage)

Output JSON.
```

---

### 2. API Endpoint (30 lines)

**Path** : `backend/api/routes/correlations.py`

**Endpoint** : `GET /api/correlations/analyzed`

**Query params** :
- `universe` : Optional list of tickers
- `window` : Time window (default '30d')
- `threshold` : Min correlation strength (default 0.7)

---

### 3. Frontend Hook (40 lines)

**Path** : `frontend/webapp/src/hooks/useCorrelationIntelligence.ts`

**Interface** :
```typescript
interface CorrelationPair {
  ticker1: string;
  ticker2: string;
  correlation: number;
  explanation: string;
  drivers: string[];
  implications: string[];
  action_type: 'HEDGE' | 'DIVERSIFY' | 'ARBITRAGE' | 'MONITOR';
}

interface CorrelationIntelligence {
  matrix: number[][];
  tickers: string[];
  interesting_pairs: CorrelationPair[];
  summary: string;
  generated_at: string;
}
```

---

### 4. Frontend Widget (200 lines)

**Path** : `frontend/webapp/src/components/widgets/CorrelationIntelligenceWidget.tsx`

**Sections** :
1. **Correlation Matrix** (heatmap with Tremor)
2. **Top Pairs** (cards with explanations)
3. **Actionable Insights** (what to do)
4. **Summary** (LLM overview)

---

## 🎨 User Experience

### Display Example

```
╔══════════════════════════════════╗
║ 🔗 Correlation Intelligence      ║
╠══════════════════════════════════╣
║ Heatmap Matrix (5x5)             ║
║ [AAPL MSFT NVDA GOOGL META]      ║
╠══════════════════════════════════╣
║ Top Correlations:                ║
║                                  ║
║ ┌──────────────────────────────┐ ║
║ │ AAPL ↔ MSFT      +0.85       │ ║
║ │ 🔍 Big Tech Sector Correlation│ ║
║ │                              │ ║
║ │ Why: Both are mega-cap tech  │ ║
║ │ companies with similar       │ ║
║ │ exposure to cloud & AI.      │ ║
║ │                              │ ║
║ │ Drivers: Sector, Macro       │ ║
║ │                              │ ║
║ │ 💡 Implication: DIVERSIFY    │ ║
║ │ Consider adding defensive    │ ║
║ │ stocks to reduce tech risk.  │ ║
║ └──────────────────────────────┘ ║
╚══════════════════════════════════╝
```

---

## ⏱️ Timeline

**Estimation** : 2-2.5h

- Backend service : 1h
- API endpoint : 15min
- Frontend hook : 15min
- Frontend widget : 45min
- Testing : 15min

---

## ✅ Success Criteria

- [x] Backend service calcule corrélations
- [x] LLM explique les corrélations
- [x] API endpoint `/api/correlations/analyzed`
- [x] Frontend hook type-safe
- [x] Widget affiche matrix + pairs + explanations
- [x] Actionable insights générés
- [x] Caching (1h validity)
- [x] Tests

---

## 📊 Impact

### Avant

- Utilisateur voit une matrice de corrélations
- Doit interpréter les chiffres lui-même
- Pas d'explication du "pourquoi"
- Pas de guidance actionable

### Après

- ✅ Corrélations + explications LLM
- ✅ "Pourquoi" ces corrélations existent
- ✅ Drivers identifiés (sector, macro, etc.)
- ✅ Actions suggérées (hedge, diversify, arbitrage)
- ✅ Time to understanding : **2 minutes**

---

## 🔗 Dependencies

**Requires** :
- ✅ FC-INT-020 (Intelligence Service)
- ✅ FC-INT-021 (Context Service)
- G4F LLM (with fallback)

**Enables** :
- 🔜 Advanced portfolio construction
- 🔜 Risk management strategies

---

**Signé** : ELENA-39  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 2-2.5h, +80 points
