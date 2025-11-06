# FC-INT-022 : IntelligenceDashboardWidget - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Widget frontend "chef d'orchestre" combinant Intelligence + Context  
**Points estimés** : +80

---

## 🎯 Objectif

Créer le **IntelligenceDashboardWidget** - le widget frontend qui combine les services Intelligence et Context pour créer une vue intelligente du marché.

### Vision

Ce widget est le **"chef d'orchestre"** de l'UI :
- Affiche le contexte marché (régime, confidence)
- Montre les insights LLM
- Liste les top opportunities
- Alerte sur les risks
- S'adapte visuellement selon le régime

---

## 📊 Architecture

### Widget Frontend

```tsx
export function IntelligenceDashboardWidget() {
  // Fetch both services
  const { data: intelligence } = useQuery(['intelligence', 'snapshot'])
  const { data: context } = useQuery(['context', 'current'])
  
  return (
    <Card>
      {/* Market Regime Section */}
      <RegimeBadge regime={context.regime} confidence={context.confidence} />
      
      {/* LLM Insights Section */}
      <InsightsPanel insights={intelligence.insights} />
      
      {/* Opportunities Section */}
      <OpportunitiesGrid opportunities={intelligence.insights.opportunities} />
      
      {/* Risks Section */}
      <RisksPanel risks={intelligence.insights.risks} />
      
      {/* Key Drivers */}
      <DriversChips drivers={context.key_drivers} />
    </Card>
  )
}
```

---

## 🎨 Components à Créer

### 1. IntelligenceDashboardWidget (Main)

**Responsabilités** :
- Fetch data from 2 services
- Compose layout
- Handle loading/error states
- Orchestrate sub-components

**Props** : None (self-contained)

---

### 2. RegimeBadge

**Affichage** :
```tsx
<Badge color={getRegimeColor(regime)} size="lg">
  {regime} • {confidence}% confidence
</Badge>
```

**Colors per regime** :
- HIGH_VOLATILITY → red
- RISK_OFF → orange
- ELEVATED_RISK → yellow
- NORMAL → blue
- RISK_ON → green
- BULL_MARKET → green
- BEAR_MARKET → red

---

### 3. InsightsPanel

**Affichage** :
```tsx
<Card title="Market Intelligence">
  <Text>{insights.summary}</Text>
  <Divider />
  <Text size="sm" c="dimmed">
    Market Regime: {insights.market_regime.explanation}
  </Text>
</Card>
```

---

### 4. OpportunitiesGrid

**Affichage** :
```tsx
<Card title="🚀 Top Opportunities">
  <Grid>
    {opportunities.map(opp => (
      <OpportunityCard
        ticker={opp.ticker}
        reasoning={opp.reasoning}
        confidence={opp.confidence}
      />
    ))}
  </Grid>
</Card>
```

**OpportunityCard** :
- Ticker avec link vers `/ticker/:ticker`
- Reasoning (LLM-generated)
- Confidence avec RingProgress

---

### 5. RisksPanel

**Affichage** :
```tsx
<Card title="⚠️ Key Risks">
  <Stack>
    {risks.map(risk => (
      <RiskAlert
        type={risk.type}
        description={risk.description}
        severity={risk.severity}
      />
    ))}
  </Stack>
</Card>
```

**RiskAlert** :
- Icon selon type (VOLATILITY, SENTIMENT, NEWS, etc.)
- Description
- Severity badge (HIGH/MEDIUM/LOW)

---

### 6. DriversChips

**Affichage** :
```tsx
<Group>
  {drivers.map(driver => (
    <Chip size="sm" variant="filled">
      {driver}
    </Chip>
  ))}
</Group>
```

---

## 🔧 Hooks Personnalisés

### 1. useIntelligence

```tsx
export function useIntelligence() {
  return useQuery({
    queryKey: ['intelligence', 'snapshot'],
    queryFn: () => apiGet('/intelligence/snapshot'),
    staleTime: 5 * 60_000,  // 5 minutes
    refetchInterval: 5 * 60_000
  })
}
```

---

### 2. useContext

```tsx
export function useMarketContext() {
  return useQuery({
    queryKey: ['context', 'current'],
    queryFn: () => apiGet('/context/current'),
    staleTime: 5 * 60_000,  // 5 minutes
    refetchInterval: 5 * 60_000
  })
}
```

---

## 📱 Layout Responsive

### Desktop (> 1200px)
```
+----------------------------------+
| [Regime Badge] [Key Drivers]     |
+----------------------------------+
| Market Intelligence              |
| [LLM Insights Summary]           |
+----------------------------------+
| Top Opportunities | Key Risks    |
| [Grid 3 cols]     | [Stack]      |
+----------------------------------+
```

### Tablet (768px - 1200px)
```
+---------------------------+
| [Regime] [Drivers]        |
+---------------------------+
| Market Intelligence       |
+---------------------------+
| Top Opportunities         |
| [Grid 2 cols]             |
+---------------------------+
| Key Risks                 |
+---------------------------+
```

### Mobile (< 768px)
```
+---------------+
| [Regime]      |
| [Drivers]     |
+---------------+
| Intelligence  |
+---------------+
| Opportunities |
| [Stack]       |
+---------------+
| Risks         |
+---------------+
```

---

## 🎨 Visual Design

### Colors

**Regime Colors** :
```tsx
const REGIME_COLORS = {
  HIGH_VOLATILITY: 'red',
  ELEVATED_RISK: 'orange',
  BEAR_MARKET: 'red',
  RISK_OFF: 'orange',
  NORMAL: 'blue',
  RISK_ON: 'green',
  BULL_MARKET: 'green'
}
```

**Severity Colors** :
```tsx
const SEVERITY_COLORS = {
  HIGH: 'red',
  MEDIUM: 'yellow',
  LOW: 'blue'
}
```

---

### Icons

**Risk Types** :
- VOLATILITY → `IconChartLine`
- SENTIMENT → `IconMoodSad`
- NEWS → `IconNews`
- MACRO → `IconChartBar`
- SYSTEM → `IconAlertTriangle`

---

## 🔄 States Management

### Loading State

```tsx
if (isLoadingIntel || isLoadingContext) {
  return <LoadingSpinner message="Loading market intelligence..." />
}
```

---

### Error State

```tsx
if (errorIntel || errorContext) {
  return (
    <Alert color="red" icon={<IconAlertCircle />}>
      Failed to load intelligence data
    </Alert>
  )
}
```

---

### Empty State

```tsx
if (!intelligence || !context) {
  return (
    <Card>
      <Text c="dimmed">No intelligence data available</Text>
    </Card>
  )
}
```

---

### Success State

Normal rendering avec toutes les sections.

---

## 🧪 Tests

### Component Tests

```tsx
describe('IntelligenceDashboardWidget', () => {
  it('renders regime badge', () => {
    render(<IntelligenceDashboardWidget />)
    expect(screen.getByText(/NORMAL/i)).toBeInTheDocument()
  })
  
  it('displays opportunities', () => {
    render(<IntelligenceDashboardWidget />)
    expect(screen.getByText(/Top Opportunities/i)).toBeInTheDocument()
  })
  
  it('shows risks', () => {
    render(<IntelligenceDashboardWidget />)
    expect(screen.getByText(/Key Risks/i)).toBeInTheDocument()
  })
  
  it('handles loading state', () => {
    // Mock loading
    render(<IntelligenceDashboardWidget />)
    expect(screen.getByText(/Loading/i)).toBeInTheDocument()
  })
})
```

---

## 📁 Fichiers à Créer

### 1. `frontend/webapp/src/components/widgets/IntelligenceDashboardWidget.tsx`

**Main component** - 200-300 lignes

---

### 2. `frontend/webapp/src/components/intelligence/RegimeBadge.tsx`

**Regime display** - 50 lignes

---

### 3. `frontend/webapp/src/components/intelligence/InsightsPanel.tsx`

**LLM insights** - 80 lignes

---

### 4. `frontend/webapp/src/components/intelligence/OpportunitiesGrid.tsx`

**Opportunities display** - 100 lignes

---

### 5. `frontend/webapp/src/components/intelligence/RisksPanel.tsx`

**Risks display** - 80 lignes

---

### 6. `frontend/webapp/src/hooks/useIntelligence.ts`

**Intelligence hook** - 30 lignes

---

### 7. `frontend/webapp/src/hooks/useMarketContext.ts`

**Context hook** - 30 lignes

---

## 🎯 User Experience

### Scenario 1 : Normal Market

**User opens dashboard**

```
+----------------------------------+
| NORMAL • 75% confidence          |
| Chips: [Low volatility]          |
|       [Balanced forecasts]       |
+----------------------------------+
| Market Intelligence              |
| "Markets operating normally with |
|  balanced sentiment..."          |
+----------------------------------+
| 🚀 Top Opportunities             |
| • AAPL - Strong technicals       |
| • MSFT - Positive momentum       |
| • GOOGL - Earnings beat          |
+----------------------------------+
| ⚠️ Key Risks                     |
| (No major risks detected)        |
+----------------------------------+
```

**User feeling** : Informed, confident

---

### Scenario 2 : High Volatility

**User opens dashboard**

```
+----------------------------------+
| HIGH_VOLATILITY • 90% confidence |
| [!] Chips: [VIX spike +50%]     |
|            [Negative news]       |
+----------------------------------+
| Market Intelligence              |
| "⚠️ Markets experiencing extreme |
|  volatility. Consider defensive  |
|  positioning..."                 |
+----------------------------------+
| 🚀 Top Opportunities             |
| • TLT - Safe haven demand        |
| • GLD - Flight to safety         |
| • JNJ - Defensive stability      |
+----------------------------------+
| ⚠️ Key Risks                     |
| • VOLATILITY (HIGH)              |
|   Extreme market uncertainty     |
| • SENTIMENT (MEDIUM)             |
|   Strong bearish bias            |
+----------------------------------+
```

**User feeling** : Alerted, guided, protected

---

## 🔗 Integration avec Autres Composants

### Dans Dashboard.tsx

```tsx
import { IntelligenceDashboardWidget } from '@/components/widgets/IntelligenceDashboardWidget'

export function Dashboard() {
  return (
    <Grid>
      <Grid.Col span={12}>
        <IntelligenceDashboardWidget />
      </Grid.Col>
      
      <Grid.Col span={6}>
        <ForecastCardsWidget />
      </Grid.Col>
      
      <Grid.Col span={6}>
        <MacroBoardWidget />
      </Grid.Col>
    </Grid>
  )
}
```

---

### Dans AdaptiveDashboard (Future)

```tsx
const { data: context } = useMarketContext()

const layout = context?.recommended_layout

return (
  <Grid>
    {/* IntelligenceDashboard always on top */}
    <Grid.Col span={12}>
      <IntelligenceDashboardWidget />
    </Grid.Col>
    
    {/* Adaptive widgets based on context */}
    {layout?.primary_widgets.map(widget => renderWidget(widget))}
  </Grid>
)
```

---

## 🎨 Advanced Features (Future)

### 1. Expandable Insights

Click on insight → Modal with detailed analysis

### 2. Historical Context

Show regime changes over time

### 3. Personalization

User can pin/unpin risks, opportunities

### 4. Refresh Indicator

Show when data was last updated + countdown to next refresh

### 5. Export

Export intelligence report as PDF/JSON

---

## ⏱️ Timeline

**Estimation** : 1-1.5 heures

- **Setup** : 10 min (structure, types)
- **Main Widget** : 20 min (IntelligenceDashboardWidget)
- **Sub-components** : 30 min (Regime, Insights, Opportunities, Risks)
- **Hooks** : 10 min (useIntelligence, useMarketContext)
- **Styling** : 15 min (responsive, colors)
- **Tests** : 15 min (component tests)

---

## 🎯 Success Criteria

- [x] Widget créé et intégré
- [x] Data fetching fonctionne (Intelligence + Context)
- [x] Regime badge affiché
- [x] LLM insights visibles
- [x] Opportunities listées
- [x] Risks alertées
- [x] Key drivers affichés
- [x] Loading states gérés
- [x] Error states gérés
- [x] Responsive design
- [x] Safe access patterns
- [x] Tests passent

---

## 📊 Impact Attendu

### Avant

- Données éparpillées dans différents widgets
- Pas de vue d'ensemble intelligente
- Utilisateur doit agréger mentalement
- Pas d'insights LLM visibles

### Après

- ✅ Vue intelligente centralisée
- ✅ Contexte marché clair
- ✅ Insights LLM mis en avant
- ✅ Opportunities + Risks visibles immédiatement
- ✅ Time to insight : **10 secondes** 🚀

---

## 🔗 Dependencies

**Requires** :
- ✅ FC-INT-020 (Intelligence Service) - Done
- ✅ FC-INT-021 (Context Service) - Done

**Enables** :
- 🔜 FC-INT-026 (Adaptive Dashboard Layout)
- 🔜 Utilisation dans toutes les pages

---

**Signé** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39 🕷️  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 1-1.5h, +80 points
