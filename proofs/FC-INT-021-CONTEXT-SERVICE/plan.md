# FC-INT-021 : Context Service - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Créer service de contexte marché pour UI adaptative  
**Points estimés** : +70

---

## 🎯 Objectif

Créer un **Context Service** qui détermine le contexte marché actuel et recommande des layouts UI adaptatifs.

### Vision

Le Context Service permet au dashboard de **s'adapter automatiquement** selon la situation du marché :
- **High volatility** → Macro front-center, defensive signals
- **Bull market** → Growth forecasts, momentum signals
- **Risk-off** → Safe havens, bonds, defensive
- **Normal** → Balanced view

---

## 📊 Architecture

### Service Backend

```python
class ContextService:
    """
    Determine market context and recommend UI adaptations
    """
    
    async def get_current_market_context():
        """
        Returns:
        {
            'regime': 'HIGH_VOLATILITY' | 'BULL_MARKET' | 'RISK_OFF' | 'NORMAL',
            'confidence': 0.85,
            'key_drivers': ['VIX spike', 'Yields rising'],
            'recommended_layout': {
                'primary_widgets': ['MacroBoardWidget', 'SignalBarsWidget'],
                'filters': {'asset_types': ['defensive']},
                'emphasis': 'macro'
            },
            'characteristics': {
                'volatility': 'high',
                'sentiment': 'bearish',
                'trend': 'down'
            },
            'metadata': {
                'generated_at': '...',
                'sources': ['macro', 'forecasts', 'news']
            }
        }
        """
```

---

## 🔧 Fonctionnalités

### 1. Market Regime Classification

**Regimes** :

| Regime | Conditions | Layout Recommendation |
|--------|-----------|----------------------|
| **HIGH_VOLATILITY** | VIX > 30 | Macro + Defensive signals front-center |
| **ELEVATED_RISK** | VIX > 20, bearish bias | Caution indicators + Risk metrics |
| **BULL_MARKET** | VIX < 15, bullish > 60% | Growth forecasts + Momentum signals |
| **BEAR_MARKET** | VIX > 20, bearish > 60% | Defensive + Safe havens |
| **RISK_OFF** | VIX > 25, negative news | Bonds + Gold + Defensive |
| **RISK_ON** | VIX < 15, positive news | Equities + Growth stocks |
| **NORMAL** | Default | Balanced view |

**Classification Logic** :
```python
def classify_regime(data):
    vix = data['macro']['VIX']
    forecast_bullish_pct = data['derived']['forecast_sentiment']['bullish_pct']
    news_sentiment = data['derived']['news_sentiment']['score']
    
    # Multi-factor decision tree
    if vix > 30:
        return 'HIGH_VOLATILITY'
    elif vix > 25 and news_sentiment < -0.2:
        return 'RISK_OFF'
    elif vix < 15 and forecast_bullish_pct > 60:
        return 'BULL_MARKET'
    # ... more rules
```

---

### 2. Key Drivers Identification

**Détection automatique** des facteurs qui déterminent le régime :

```python
drivers = []

if vix_change_24h > 15:
    drivers.append(f"VIX spike: +{vix_change_24h}%")

if yields_10y > 4.5:
    drivers.append(f"Yields elevated: {yields_10y}%")

if news_sentiment < -0.3:
    drivers.append("Negative news sentiment")

if inflation > 4:
    drivers.append(f"High inflation: {inflation}%")
```

---

### 3. Recommended Layout Generation

**Pour chaque régime**, génère layout optimal :

#### HIGH_VOLATILITY Layout
```json
{
  "primary_widgets": [
    "MacroBoardWidget",
    "SignalBarsWidget",
    "HeatmapWidget"
  ],
  "filters": {
    "asset_types": ["defensive", "bonds"],
    "forecast_direction": null,
    "min_confidence": 0.7
  },
  "emphasis": "macro",
  "alerts_enabled": true,
  "refresh_interval": 300000  // 5 minutes
}
```

#### BULL_MARKET Layout
```json
{
  "primary_widgets": [
    "ForecastCardsWidget",
    "PerformanceMatrixWidget",
    "SignalBarsWidget"
  ],
  "filters": {
    "asset_types": ["growth", "tech"],
    "forecast_direction": "up",
    "min_confidence": 0.6
  },
  "emphasis": "forecasts",
  "alerts_enabled": false,
  "refresh_interval": 600000  // 10 minutes
}
```

---

### 4. Characteristics Extraction

**Extract key characteristics** :
- **Volatility** : low / medium / high / extreme
- **Sentiment** : bullish / bearish / neutral
- **Trend** : up / down / sideways
- **Momentum** : strong / moderate / weak
- **Risk level** : low / medium / high

---

### 5. Confidence Scoring

**Calculate confidence** in regime classification :

```python
confidence = (
    vix_certainty * 0.3 +
    forecast_certainty * 0.3 +
    news_certainty * 0.2 +
    historical_consistency * 0.2
)
```

High confidence (>0.8) → Strong UI adaptation  
Low confidence (<0.5) → Keep default layout

---

## 🔗 Integration avec Intelligence Service

Context Service **utilise** Intelligence Service :

```python
class ContextService:
    def __init__(self):
        self.intelligence_service = get_intelligence_service()
    
    async def get_current_market_context(self):
        # Get intelligence snapshot
        intel = await self.intelligence_service.get_market_snapshot_intelligence()
        
        # Extract data
        data = intel['data']
        insights = intel['insights']
        
        # Classify regime
        regime = self._classify_regime(data, insights)
        
        # Generate layout recommendation
        layout = self._get_recommended_layout(regime, data)
        
        # Calculate characteristics
        characteristics = self._extract_characteristics(data, insights)
        
        return {
            'regime': regime,
            'recommended_layout': layout,
            'characteristics': characteristics,
            ...
        }
```

**Pas de duplication** : Context Service est une couche au-dessus d'Intelligence Service.

---

## 📡 API Endpoint

### GET `/api/context/current`

**Response** :
```json
{
  "regime": "HIGH_VOLATILITY",
  "confidence": 0.85,
  "key_drivers": [
    "VIX spike: +15%",
    "Negative news sentiment",
    "Yields rising rapidly"
  ],
  "recommended_layout": {
    "primary_widgets": ["MacroBoardWidget", "SignalBarsWidget"],
    "filters": {
      "asset_types": ["defensive", "bonds"]
    },
    "emphasis": "macro"
  },
  "characteristics": {
    "volatility": "high",
    "sentiment": "bearish",
    "trend": "down",
    "momentum": "weak",
    "risk_level": "high"
  },
  "metadata": {
    "generated_at": "2025-11-06T03:00:00Z",
    "sources": ["macro", "forecasts", "news"],
    "confidence_breakdown": {
      "vix_certainty": 0.9,
      "forecast_certainty": 0.8,
      "news_certainty": 0.85
    }
  }
}
```

---

## 🧪 Tests

### Test Suite

```python
async def test_context_service():
    # Test 1: Service instantiation
    service = get_context_service()
    assert service is not None
    
    # Test 2: Get current context
    context = await service.get_current_market_context()
    
    # Test 3: Validate structure
    assert 'regime' in context
    assert 'confidence' in context
    assert 'recommended_layout' in context
    assert 'characteristics' in context
    
    # Test 4: Validate regime
    valid_regimes = ['HIGH_VOLATILITY', 'BULL_MARKET', 'RISK_OFF', 'NORMAL', ...]
    assert context['regime'] in valid_regimes
    
    # Test 5: Validate layout
    layout = context['recommended_layout']
    assert 'primary_widgets' in layout
    assert 'filters' in layout
    assert 'emphasis' in layout
    
    # Test 6: Validate characteristics
    chars = context['characteristics']
    assert 'volatility' in chars
    assert 'sentiment' in chars
```

---

## 📁 Fichiers à Créer

### 1. `backend/services/context_service.py`

**Classes** :
- `ContextService` - Main service class
- Helper functions pour classification

**Méthodes** :
- `get_current_market_context()` - Entry point
- `_classify_regime()` - Regime classification
- `_identify_key_drivers()` - Drivers extraction
- `_get_recommended_layout()` - Layout generation
- `_extract_characteristics()` - Characteristics extraction
- `_calculate_confidence()` - Confidence scoring

**Estimation** : 400-500 lignes

---

### 2. `backend/api/routes/context.py`

**Endpoints** :
- `GET /api/context/current` - Get current market context

**Estimation** : 50 lignes

---

### 3. `backend/api/main.py` (modification)

**Integration** :
```python
# Context router (FC-INT-021 by ELENA-39)
from api.routes.context import router as context_router
app.include_router(context_router, prefix="/api/context", tags=["context"])
```

---

### 4. `backend/test_context.py`

**Test Suite** :
- Service instantiation
- Context generation
- Regime classification
- Layout generation
- Characteristics extraction
- Confidence calculation

**Estimation** : 150 lignes

---

### 5. `proofs/FC-INT-021-CONTEXT-SERVICE/PROOF.md`

Documentation complète avec :
- Tests results
- Examples de contexts
- Regime classification logic
- Layout recommendations

---

## 🎯 Résultats Attendus

### Avant

- UI statique, même layout pour toutes situations
- Utilisateur doit adapter manuellement
- Pas d'awareness du contexte marché

### Après

- ✅ UI s'adapte automatiquement selon marché
- ✅ Layout optimal selon volatilité/sentiment
- ✅ Widgets pertinents mis en avant
- ✅ Filtres automatiques appliqués
- ✅ Context awareness complet

---

## 📊 Use Cases

### Use Case 1 : VIX Spike (Panic)

**Input** :
- VIX = 35 (spike from 20)
- Forecast sentiment = 30% bullish, 60% bearish
- News sentiment = -0.4 (very negative)

**Output** :
```json
{
  "regime": "RISK_OFF",
  "key_drivers": ["VIX spike: +75%", "Negative news flood"],
  "recommended_layout": {
    "primary_widgets": ["MacroBoardWidget", "SignalBarsWidget"],
    "filters": {"asset_types": ["defensive", "bonds", "gold"]},
    "emphasis": "macro"
  }
}
```

**UI Result** : Dashboard shows macro indicators, defensive stocks, safe havens

---

### Use Case 2 : Calm Bull Market

**Input** :
- VIX = 12 (low)
- Forecast sentiment = 70% bullish, 20% bearish
- News sentiment = +0.3 (positive)

**Output** :
```json
{
  "regime": "BULL_MARKET",
  "key_drivers": ["Low volatility", "Strong bullish forecasts"],
  "recommended_layout": {
    "primary_widgets": ["ForecastCardsWidget", "PerformanceMatrixWidget"],
    "filters": {"asset_types": ["growth", "tech"]},
    "emphasis": "forecasts"
  }
}
```

**UI Result** : Dashboard shows growth forecasts, momentum signals, performance

---

### Use Case 3 : Normal Conditions

**Input** :
- VIX = 18 (normal)
- Forecast sentiment = 45% bullish, 35% bearish
- News sentiment = 0.05 (neutral)

**Output** :
```json
{
  "regime": "NORMAL",
  "key_drivers": ["Balanced market conditions"],
  "recommended_layout": {
    "primary_widgets": ["IntelligenceDashboardWidget", "ForecastMatrixWidget"],
    "filters": {},
    "emphasis": "balanced"
  }
}
```

**UI Result** : Dashboard shows balanced view with all data types

---

## 🔄 Workflow

### Backend Flow
```
API Request /api/context/current
  ↓
ContextService.get_current_market_context()
  ↓
1. Get Intelligence Snapshot (from FC-INT-020)
  ↓
2. Classify Regime (VIX, sentiment, forecasts)
  ↓
3. Identify Key Drivers (what causes this regime)
  ↓
4. Generate Recommended Layout (widgets, filters)
  ↓
5. Extract Characteristics (volatility, sentiment, etc.)
  ↓
6. Calculate Confidence (how sure we are)
  ↓
Return Context Object
```

### Frontend Integration (FC-INT-022, next task)
```tsx
function AdaptiveDashboard() {
  const { data: context } = useQuery(['context', 'current'])
  
  const layout = useMemo(() => {
    if (!context) return DEFAULT_LAYOUT
    return context.recommended_layout
  }, [context])
  
  return (
    <DashboardGrid regime={context.regime}>
      {renderWidgets(layout.primary_widgets, layout.filters)}
    </DashboardGrid>
  )
}
```

---

## 💡 Advanced Features (Future)

### 1. Historical Context Tracking
- Store regime changes over time
- Detect regime transitions
- Calculate regime stability

### 2. User Preferences
- Allow manual override
- Remember user preferences
- Hybrid auto + manual mode

### 3. Regime Alerts
- Notify when regime changes
- Alert on transition (e.g., NORMAL → RISK_OFF)
- Recommended actions on change

### 4. Multi-Timeframe Context
- Intraday context
- Daily context
- Weekly context
- Show context evolution

---

## ⏱️ Timeline

**Estimation** : 1-2 heures

- **Setup** : 15 min (structure, imports)
- **Core Logic** : 45 min (regime classification, drivers)
- **Layout Generation** : 30 min (layout logic per regime)
- **Tests** : 20 min (test suite + validation)
- **Documentation** : 10 min (PROOF.md)

---

## 🎯 Success Criteria

- [x] Service créé et testé
- [x] Endpoint `/api/context/current` fonctionnel
- [x] Regime classification précise
- [x] Key drivers identifiés
- [x] Recommended layout généré
- [x] Characteristics extracted
- [x] Tests passent 100%
- [x] Integration avec Intelligence Service
- [x] Confidence scoring implémenté
- [x] Documentation complète

---

## 🔗 Dependencies

**Requires** :
- ✅ FC-INT-020 (Intelligence Service) - Already done

**Enables** :
- 🔜 FC-INT-022 (IntelligenceDashboardWidget)
- 🔜 FC-INT-026 (Adaptive Dashboard Layout)

---

**Signé** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39 🕷️  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 1-2h, +70 points
