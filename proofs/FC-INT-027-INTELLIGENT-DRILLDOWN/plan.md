# FC-INT-027 : Intelligent Drill-Down - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Navigation intelligente depuis n'importe quel widget vers détails  
**Points estimés** : +80

---

## 🎯 Objectif

Créer un **système de drill-down intelligent** qui permet à l'utilisateur de cliquer sur n'importe quel élément (ticker, forecast, news, correlation) et d'accéder automatiquement aux détails pertinents avec **contexte conservé**.

**Vision** : Un clic sur "AAPL" dans n'importe quel widget → Page détaillée avec toutes les infos (forecasts, news, correlations, recommendations) **pour ce ticker**.

---

## 🧠 Problème Actuel

**Navigation actuelle** :
- ❌ Widgets isolés (pas de liens vers détails)
- ❌ User doit chercher manuellement le ticker dans d'autres pages
- ❌ Pas de contexte conservé (pourquoi on regarde ce ticker ?)
- ❌ Pas de "retour" intelligent

**Exemple** :
- User voit "AAPL" dans Recommendations Widget
- Veut voir les détails
- Doit aller manuellement sur page Stocks ou Forecasts
- Chercher "AAPL"
- Perd le contexte (pourquoi AAPL était recommandé)

**Frustrant !** ❌

---

## 💡 Solution : Intelligent Drill-Down

### Architecture

```
Widget Click (AAPL) → DrillDownContext → TickerDetailPage
                         ↓
                    Context preserved:
                    - Source widget
                    - Recommendation reason
                    - Market regime
                    - Related data
```

### Flow

1. **User clique** sur "AAPL" dans RecommendationsWidget
2. **DrillDownContext** capture :
   - Ticker : "AAPL"
   - Source : "recommendations"
   - Reason : "Strong bullish forecast + positive news"
   - Regime : "BULL_MARKET"
3. **Navigation** vers `/ticker/AAPL`
4. **TickerDetailPage** affiche :
   - Forecasts pour AAPL
   - News récentes pour AAPL
   - Correlations avec AAPL
   - Recommendations pour AAPL
   - **Context badge** : "Recommended in BULL_MARKET"
   - **Back button** : "Return to Recommendations"

---

## 🏗️ Implementation

### 1. DrillDown Context

**Nouveau fichier** : `frontend/webapp/src/contexts/DrillDownContext.tsx`

**Responsabilités** :
- Stocker le contexte de navigation
- Source widget
- Raison du drill-down
- Breadcrumb navigation
- History stack

**Context API** :
```typescript
interface DrillDownContext {
  currentDrillDown: DrillDownState | null;
  navigateToTicker: (ticker: string, context: DrillDownMetadata) => void;
  navigateToForecast: (forecast: Forecast, context: DrillDownMetadata) => void;
  navigateToNews: (news: NewsItem, context: DrillDownMetadata) => void;
  goBack: () => void;
  clearContext: () => void;
}

interface DrillDownMetadata {
  source: 'recommendations' | 'forecasts' | 'intelligence' | 'correlations' | 'news';
  reason?: string;
  regime?: MarketRegime;
  additionalData?: Record<string, any>;
}
```

---

### 2. TickerDetailPage

**Nouveau fichier** : `frontend/webapp/src/pages/TickerDetail.tsx`

**Sections** :
1. **Header** : Ticker + Context Badge + Back Button
2. **Quick Stats** : Price, Change, Volume
3. **Tabs** :
   - Overview (forecasts + key metrics)
   - News (filtered by ticker)
   - Correlations (pairs with this ticker)
   - Recommendations (if applicable)
   - Historical Performance

**Props** :
- `ticker` : from URL params
- `context` : from DrillDownContext

---

### 3. Drillable Components

**Composants à rendre "drillable"** :
- `RecommendationCard` → Click on ticker
- `ForecastCard` → Click on ticker
- `NewsCard` → Click on ticker/company
- `CorrelationPair` → Click on either ticker
- `OpportunityCard` → Click on ticker

**Pattern** :
```tsx
import { useDrillDown } from '@/contexts/DrillDownContext';

function RecommendationCard({ recommendation }) {
  const { navigateToTicker } = useDrillDown();

  const handleClick = () => {
    navigateToTicker(recommendation.ticker, {
      source: 'recommendations',
      reason: recommendation.reasoning,
      regime: currentRegime,
      additionalData: { score: recommendation.score }
    });
  };

  return (
    <Card onClick={handleClick} style={{ cursor: 'pointer' }}>
      {/* ... */}
    </Card>
  );
}
```

---

### 4. Context Preservation UI

**Components** :

#### A. ContextBreadcrumb
```tsx
// Shows: Dashboard > Recommendations > AAPL (Recommended)
<Breadcrumbs>
  <Anchor onClick={goToDashboard}>Dashboard</Anchor>
  <Anchor onClick={goBack}>Recommendations</Anchor>
  <Text>AAPL</Text>
</Breadcrumbs>
```

#### B. ContextBadge
```tsx
// Shows why user is here
<Badge color="blue" leftSection={<IconSparkles />}>
  Recommended in BULL_MARKET
</Badge>
```

#### C. BackButton
```tsx
// Smart back button
<Button onClick={goBack} leftSection={<IconArrowLeft />}>
  Back to Recommendations
</Button>
```

---

### 5. Router Integration

**Mise à jour** : `frontend/webapp/src/App.tsx`

**Nouvelle route** :
```tsx
<Route path="/ticker/:ticker" element={<TickerDetailPage />} />
```

**Navigation** :
```tsx
const navigate = useNavigate();

const navigateToTicker = (ticker, context) => {
  // Save context
  setDrillDownContext({ ticker, ...context });
  // Navigate
  navigate(`/ticker/${ticker}`);
};
```

---

## 🎨 User Experience

### Scenario 1 : Depuis Recommendations

**User journey** :
1. User sur Dashboard
2. Voit "AAPL" dans SmartRecommendationsWidget
3. Clique sur "AAPL"
4. → Page `/ticker/AAPL` s'ouvre
5. Voit :
   - Badge : "Recommended for BULL_MARKET"
   - Forecasts pour AAPL
   - News récentes AAPL
   - Correlations avec AAPL
   - Back button : "Return to Dashboard"

---

### Scenario 2 : Depuis Correlations

**User journey** :
1. User sur Dashboard
2. Voit paire "AAPL ↔ MSFT (0.85)" dans CorrelationWidget
3. Clique sur "AAPL"
4. → Page `/ticker/AAPL` s'ouvre
5. Voit :
   - Badge : "Correlated with MSFT (0.85)"
   - Liste des autres corrélations AAPL
   - Forecasts pour AAPL
   - Back button : "Return to Correlations"

---

### Scenario 3 : Depuis News

**User journey** :
1. User sur News page
2. Voit article "Apple announces..."
3. Clique sur "AAPL" tag
4. → Page `/ticker/AAPL` s'ouvre
5. Voit :
   - Badge : "From news: Apple announces..."
   - Toutes les news AAPL
   - Forecast impact de la news
   - Back button : "Return to News"

---

## 📊 Architecture

### State Management

```
DrillDownContext (React Context)
├── currentDrillDown (state)
│   ├── ticker
│   ├── source
│   ├── reason
│   ├── regime
│   └── additionalData
├── history (stack)
│   └── Previous drill-downs
└── Methods
    ├── navigateToTicker()
    ├── navigateToForecast()
    ├── navigateToNews()
    ├── goBack()
    └── clearContext()
```

### Component Hierarchy

```
App
├── DrillDownProvider
│   └── DrillDownContext
└── Routes
    ├── Dashboard
    │   └── Widgets (drillable)
    ├── TickerDetailPage
    │   ├── ContextBreadcrumb
    │   ├── ContextBadge
    │   ├── BackButton
    │   └── TickerContent
    │       ├── Forecasts
    │       ├── News
    │       ├── Correlations
    │       └── Recommendations
    └── Other pages
```

---

## ⏱️ Timeline

**Estimation** : 2-3h

- DrillDownContext : 30min
- TickerDetailPage : 1h
- Make components drillable : 45min
- Context UI (breadcrumbs, badges, back) : 30min
- Testing : 15min

---

## ✅ Success Criteria

- [ ] User peut cliquer sur ticker dans n'importe quel widget
- [ ] Navigation vers page détaillée
- [ ] Contexte conservé (source, reason)
- [ ] Breadcrumb navigation visible
- [ ] Context badge explique pourquoi user est ici
- [ ] Back button intelligent (retour à source)
- [ ] Page détaillée charge données pertinentes
- [ ] Responsive (desktop/tablet/mobile)
- [ ] Performance : <200ms transition

---

## 📈 Impact

### Avant

- User voit "AAPL" recommandé
- Doit chercher manuellement AAPL ailleurs
- Perd le contexte de la recommandation
- **3-4 clics** pour voir détails
- **Frustration**

### Après

- ✅ **1 clic** sur "AAPL" → détails complets
- ✅ Contexte conservé (pourquoi AAPL recommandé)
- ✅ Navigation fluide
- ✅ Retour intelligent
- ✅ Toutes les infos pertinentes en 1 page

**Time to insight** : **4 minutes → 30 secondes** (80% reduction)

---

## 🔗 Dependencies

**Requires** :
- ✅ React Router (already installed)
- ✅ Existing hooks (useForecasts, useNews, etc.)
- ✅ Existing widgets

**Enables** :
- 🔜 FC-INT-028 (Smart Alerts) - Drill-down from alerts
- 🔜 Analytics (track user navigation patterns)
- 🔜 Personalization (learn user interests)

---

## 🎯 Technical Specs

### URL Structure

```
/ticker/:ticker                    # Main ticker page
/ticker/:ticker?tab=news           # Specific tab
/ticker/:ticker?tab=correlations   # Correlations tab
/ticker/:ticker?source=recommendations  # With context
```

### Context Persistence

**Use** :
- React Context (in-memory, current session)
- LocalStorage (optional, persist across sessions)

**Structure** :
```typescript
interface DrillDownState {
  ticker: string;
  source: DrillDownSource;
  reason?: string;
  regime?: MarketRegime;
  timestamp: string;
  previousUrl: string;
}
```

### Data Fetching

**Parallel fetching** :
```typescript
const { data: forecasts } = useForecasts({ ticker });
const { data: news } = useNews({ ticker });
const { data: correlations } = useCorrelations({ ticker });

// All fetch in parallel, no waterfall
```

---

## 🚀 Future Enhancements

### Phase 2 (optional)
- 📊 Drill-down from charts (click on data point)
- 🔗 Related tickers suggestions
- 📈 Compare mode (drill-down to 2 tickers side-by-side)
- 🎯 Smart recommendations "People who viewed AAPL also viewed..."
- 📱 Mobile swipe navigation
- 🧠 ML-powered "Why you might be interested" suggestions

---

**Signé** : ELENA-39  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 2-3h, +80 points
