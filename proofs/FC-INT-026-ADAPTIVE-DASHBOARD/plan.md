# FC-INT-026 : Adaptive Dashboard Layout - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Dashboard qui s'adapte dynamiquement au market regime  
**Points estimés** : +90

---

## 🎯 Objectif

Créer un **Dashboard Adaptatif** qui réorganise automatiquement son layout et ses widgets selon le **market regime** détecté par le Context Service.

**Vision** : Le dashboard ne doit plus être statique - il doit **réagir intelligemment** au contexte du marché.

---

## 🧠 Problème Actuel

**Dashboard actuel** :
- ❌ Layout fixe (même disposition pour BULL et BEAR market)
- ❌ Widgets toujours affichés (même si non pertinents)
- ❌ Pas de priorisation selon contexte
- ❌ Utilisateur doit manuellement chercher l'info pertinente

**Exemple** :
- En **BULL_MARKET** → Utilisateur veut voir **opportunities, momentum**
- En **HIGH_VOLATILITY** → Utilisateur veut voir **risks, correlations, hedging**
- En **RISK_OFF** → Utilisateur veut voir **defensive stocks, macro alerts**

Actuellement : **Même layout pour tous** 🤦

---

## 💡 Solution : Adaptive Dashboard Layout

### Architecture

```typescript
Market Context (API) → Adaptive Layout Engine → Dynamic Component Rendering
```

### Flow

1. **Context Service** détecte le regime (`BULL_MARKET`, `HIGH_VOLATILITY`, etc.)
2. **Adaptive Layout Engine** (frontend) décide :
   - Quels widgets afficher
   - Ordre des widgets
   - Taille des widgets
   - Filtres par défaut
3. **Dashboard** se re-render automatiquement

---

## 🏗️ Implementation

### 1. Backend : Layout Recommendations (déjà fait ✅)

Le **Context Service (FC-INT-021)** fournit déjà :

```json
{
  "regime": "HIGH_VOLATILITY",
  "recommended_layout": {
    "priority_widgets": ["risks", "correlations", "alerts"],
    "secondary_widgets": ["forecasts", "news"],
    "filters": {
      "default_risk_level": "high",
      "default_time_horizon": "1d"
    }
  }
}
```

**Donc backend = déjà prêt !** ✅

---

### 2. Frontend : Adaptive Layout Engine

**Nouveau fichier** : `frontend/webapp/src/services/adaptiveLayoutService.ts`

**Responsabilités** :
- Interpréter les recommendations du Context Service
- Mapper `priority_widgets` → Components React
- Gérer l'ordre d'affichage
- Appliquer les filtres par défaut

**Example logic** :

```typescript
function getLayoutForRegime(regime: MarketRegime, recommendations: LayoutRecommendations) {
  const widgetMap = {
    'intelligence': IntelligenceDashboardWidget,
    'recommendations': SmartRecommendationsWidget,
    'correlations': CorrelationIntelligenceWidget,
    'forecasts': ForecastCardsWidget,
    'risks': RisksPanel,
    'news': NewsWidget,
    // ... etc
  };

  const priorityWidgets = recommendations.priority_widgets.map(name => widgetMap[name]);
  const secondaryWidgets = recommendations.secondary_widgets.map(name => widgetMap[name]);

  return {
    topRow: priorityWidgets,
    bottomRow: secondaryWidgets,
    defaultFilters: recommendations.filters
  };
}
```

---

### 3. Dashboard Component Refactor

**Fichier** : `frontend/webapp/src/pages/Dashboard.tsx`

**Modifications** :

#### Avant (statique) :

```tsx
<Dashboard>
  <IntelligenceWidget />
  <ForecastsWidget />
  <NewsWidget />
  <MacroWidget />
</Dashboard>
```

#### Après (adaptatif) :

```tsx
<Dashboard>
  {layout.topRow.map(Widget => <Widget key={Widget.name} />)}
  
  <Divider />
  
  {layout.bottomRow.map(Widget => <Widget key={Widget.name} />)}
</Dashboard>
```

**Plus** :
- Badge affichant le regime actuel
- Bouton "Switch to manual mode" (désactiver adaptation)
- Smooth transitions (Framer Motion)

---

## 🎨 User Experience

### Scenario 1 : BULL_MARKET

**Dashboard affiche** :
1. 🎯 **Top** : Opportunities, Recommendations, Forecasts (bullish)
2. 📰 **Middle** : News (positive sentiment prioritized)
3. 📊 **Bottom** : Macro indicators, Performance

**Filters par défaut** :
- Direction : "UP"
- Confidence : >0.7
- Risk : "moderate"

---

### Scenario 2 : HIGH_VOLATILITY

**Dashboard affiche** :
1. 🚨 **Top** : Risks Panel, Alerts, Correlations
2. 🛡️ **Middle** : Hedging recommendations, Defensive stocks
3. 📈 **Bottom** : Volatility charts, VIX

**Filters par défaut** :
- Risk : "high"
- Time horizon : "1d" (short-term)
- Volatility : >0.3

---

### Scenario 3 : RISK_OFF

**Dashboard affiche** :
1. 🛑 **Top** : Macro alerts, Safe havens (bonds, gold)
2. 📉 **Middle** : Market regime explanation, Flight-to-quality indicators
3. 🔍 **Bottom** : Defensive sectors, Low-beta stocks

**Filters par défaut** :
- Sector : "Consumer Staples", "Utilities", "Healthcare"
- Beta : <0.8

---

## 🧩 Components Architecture

```
Dashboard.tsx (main)
├── AdaptiveLayoutProvider (context)
│   ├── useMarketContext (hook)
│   └── useAdaptiveLayout (hook)
├── RegimeBadge (shows current regime)
├── LayoutModeToggle (manual/auto)
└── DynamicWidgetGrid
    ├── PriorityRow (top widgets)
    ├── SecondaryRow (middle widgets)
    └── TertiaryRow (bottom widgets)
```

---

## ⏱️ Timeline

**Estimation** : 3h

- Adaptive Layout Service : 1h
- Dashboard refactor : 1h
- UI polish (transitions, badges) : 30min
- Testing : 30min

---

## ✅ Success Criteria

- [ ] Dashboard layout change automatiquement selon regime
- [ ] Widgets affichés selon priorité (Context Service)
- [ ] Filtres par défaut appliqués selon recommendations
- [ ] Smooth transitions entre layouts
- [ ] Badge regime visible
- [ ] Mode manuel disponible (toggle)
- [ ] Performance : pas de lag lors du changement
- [ ] Responsive (desktop/tablet/mobile)

---

## 📊 Impact

### Avant

- Utilisateur scroll pour trouver info pertinente
- Même layout pour tous les regimes
- Perte de temps : 2-3 minutes par session

### Après

- ✅ Info pertinente **immédiatement visible**
- ✅ Layout optimisé pour le contexte actuel
- ✅ Time to action : **10 secondes**
- ✅ Expérience personnalisée
- ✅ Intelligence adaptative

**Gain de temps** : **80% reduction** (3min → 30sec)

---

## 🔗 Dependencies

**Requires** :
- ✅ FC-INT-021 (Context Service) - DONE
- ✅ FC-INT-020 (Intelligence Service) - DONE
- ✅ Existing widgets (LUCIE-13) - DONE

**Enables** :
- 🔜 FC-INT-027 (Intelligent Drill-Down)
- 🔜 User behavior analytics
- 🔜 A/B testing layouts

---

## 🎯 Technical Specs

### API Usage

**Endpoint** : `GET /api/context/current`

**Response** :
```json
{
  "regime": "HIGH_VOLATILITY",
  "confidence": 0.85,
  "key_drivers": ["VIX spike", "Earnings uncertainty"],
  "recommended_layout": {
    "priority_widgets": ["risks", "correlations", "alerts"],
    "secondary_widgets": ["forecasts", "news"],
    "filters": {
      "default_risk_level": "high",
      "default_time_horizon": "1d"
    }
  }
}
```

### State Management

**Use React Context** :
```typescript
interface AdaptiveLayoutContext {
  currentRegime: MarketRegime;
  layout: LayoutConfig;
  isManualMode: boolean;
  toggleMode: () => void;
  refreshLayout: () => void;
}
```

### Widget Registry

**Centralized widget mapping** :
```typescript
const WIDGET_REGISTRY = {
  intelligence: IntelligenceDashboardWidget,
  recommendations: SmartRecommendationsWidget,
  correlations: CorrelationIntelligenceWidget,
  forecasts: ForecastCardsWidget,
  news: NewsWidget,
  macro: MacroBoardWidget,
  // ... etc
};
```

---

## 🚀 Future Enhancements

### Phase 2 (optional)
- 📊 User personalization (save preferred layout)
- 📈 Layout performance analytics
- 🔔 Notifications on regime change
- 🎨 Custom themes per regime
- 📱 Mobile-specific layouts

---

**Signé** : ELENA-39  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 3h, +90 points
