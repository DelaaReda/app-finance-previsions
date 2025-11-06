# FC-UX-002 : News Signal Radar - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Visualisation sexy des news avec treemap/heatmap + sentiment  
**Points estimés** : +120

---

## 🎯 Objectif

Créer un **News Signal Radar** - Visualisation interactive et sexy des actualités financières avec :
- Treemap/Heatmap par secteur/score
- Time decay badges (fraîcheur)
- Sentiment histograms
- Animations temps réel
- **WOW EFFECT garanti** ✨

**Vision** : La page la plus visuelle de l'app - impression immédiate "ce produit est différent"

---

## 💡 Pourquoi ça va ÉPATER le client

1. **Visuellement spectaculaire** : Treemap coloré + animations
2. **Information dense** : 50+ news en 1 vue
3. **Interactif** : Hover, click, drill-down
4. **Temps réel** : Colors qui changent selon sentiment
5. **Professional** : Niveau Bloomberg Terminal
6. **Unique** : Personne n'a ça dans finance apps

---

## 🎨 Design Visuel

### Layout Principal

```
┌─────────────────────────────────────────────────────────┐
│  News Signal Radar                            🔴 Live   │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────── TREEMAP ────────────────────┐    │
│  │                                                  │    │
│  │  ┌──────┐  ┌────────────┐  ┌─────┐            │    │
│  │  │ AAPL │  │   MSFT     │  │NVDA │            │    │
│  │  │ 🟢   │  │    🟢      │  │ 🟢  │            │    │
│  │  └──────┘  └────────────┘  └─────┘            │    │
│  │                                                  │    │
│  │  ┌──────────┐  ┌─────┐  ┌──────┐              │    │
│  │  │  TSLA    │  │ AMD │  │ META │              │    │
│  │  │   🔴     │  │ 🟡  │  │  🟢  │              │    │
│  │  └──────────┘  └─────┘  └──────┘              │    │
│  │                                                  │    │
│  └──────────────────────────────────────────────┘    │
│                                                           │
│  Sentiment Distribution:  🟢 65%  🟡 25%  🔴 10%        │
│                                                           │
│  ┌─────────────── FILTERS ─────────────────┐           │
│  │ [All] [Tech] [Finance] [Energy]          │           │
│  │ [Today] [This Week] [This Month]          │           │
│  └───────────────────────────────────────────┘           │
│                                                           │
│  ┌────────────── NEWS LIST ──────────────┐              │
│  │ 🟢 AAPL: Apple announces... (2h ago)   │              │
│  │ 🔴 TSLA: Tesla faces... (5min ago)     │              │
│  │ 🟡 MSFT: Microsoft reports... (1h ago) │              │
│  └────────────────────────────────────────┘              │
└───────────────────────────────────────────────────────┘
```

---

## 🏗️ Implementation

### 1. News Signal Radar Page

**Fichier** : `frontend/webapp/src/pages/NewsSignalRadar.tsx`

**Components** :
- Header avec live indicator
- Treemap visualization (Tremor ou D3)
- Sentiment distribution bar
- Filters (sector, timeframe)
- News list (detailed view)

---

### 2. Treemap Component

**Fichier** : `frontend/webapp/src/components/news/NewsTreemap.tsx`

**Features** :
- ✅ Size = nombre d'articles par ticker
- ✅ Color = sentiment moyen (vert/jaune/rouge)
- ✅ Hover = tooltip avec détails
- ✅ Click = drill-down to ticker
- ✅ Animations smooth

**Tech** :
- **Tremor AreaChart** (si possible) ou
- **Recharts Treemap** ou
- **D3.js** (custom mais plus flexible)

**Data Structure** :
```typescript
interface NewsSignalData {
  ticker: string;
  count: number; // Size of box
  avgSentiment: number; // 0-1 (0=negative, 1=positive)
  recentNews: NewsItem[];
  sector: string;
}
```

---

### 3. Sentiment Distribution

**Component** : Simple progress bars

```tsx
<Group>
  <Badge color="green">Positive: {positivePercent}%</Badge>
  <Progress value={positivePercent} color="green" />
  
  <Badge color="yellow">Neutral: {neutralPercent}%</Badge>
  <Progress value={neutralPercent} color="yellow" />
  
  <Badge color="red">Negative: {negativePercent}%</Badge>
  <Progress value={negativePercent} color="red" />
</Group>
```

---

### 4. Time Decay Badges

**Visual** : Badge avec couleur selon fraîcheur

```tsx
function getFreshnessColor(ageMinutes: number) {
  if (ageMinutes < 10) return 'green'; // Fresh
  if (ageMinutes < 60) return 'yellow'; // Recent
  if (ageMinutes < 240) return 'orange'; // Old
  return 'red'; // Stale
}

<Badge color={getFreshnessColor(age)}>
  {formatTimeAgo(timestamp)}
</Badge>
```

---

### 5. Data Processing

**Hook** : `useNewsSignals.ts`

```typescript
export function useNewsSignals(filters: NewsFilters) {
  const { data: news } = useNews();
  
  const processedData = useMemo(() => {
    // Group by ticker
    const byTicker = groupBy(news, 'ticker');
    
    // Calculate stats per ticker
    return Object.entries(byTicker).map(([ticker, items]) => ({
      ticker,
      count: items.length,
      avgSentiment: mean(items.map(i => i.sentiment_score)),
      recentNews: items.slice(0, 3),
      sector: getSector(ticker),
      freshness: min(items.map(i => getAgeMinutes(i.timestamp)))
    }));
  }, [news, filters]);
  
  return { data: processedData };
}
```

---

## 🎨 User Experience

### Scenario 1 : Vue d'ensemble

**User opens /news/radar** :
1. Sees animated treemap loading
2. Big boxes = tickers avec beaucoup de news
3. Colors = sentiment (vert/rouge)
4. Instantly understands market mood
5. **"Wow, this is beautiful"**

---

### Scenario 2 : Drill-Down

**User hovers over AAPL box** :
1. Tooltip appears :
   - "AAPL: 12 articles"
   - "Avg sentiment: 0.78 (Positive)"
   - "Latest: Apple announces..."
   - "Last update: 5 min ago"
2. Box highlights
3. User clicks
4. → Navigates to /ticker/AAPL with news context

---

### Scenario 3 : Filter

**User clicks "Tech" sector** :
1. Treemap re-animates
2. Only tech stocks shown
3. Smooth transition
4. Sentiment distribution updates
5. News list filters

---

## 📊 Architecture

### Data Flow

```
useNews() → Raw news feed
    ↓
useNewsSignals() → Process & aggregate
    ↓
{
  ticker: 'AAPL',
  count: 12,
  avgSentiment: 0.78,
  sector: 'Technology',
  ...
}
    ↓
NewsTreemap → Visual representation
    ↓
User interaction → Drill-down or filter
```

### Color Mapping

```typescript
function getSentimentColor(sentiment: number): string {
  if (sentiment > 0.6) return '#10b981'; // Green (positive)
  if (sentiment > 0.4) return '#fbbf24'; // Yellow (neutral)
  return '#ef4444'; // Red (negative)
}
```

---

## ⏱️ Timeline

**Estimation** : 3-4h

- NewsTreemap component : 1.5h
- NewsSignalRadar page : 1h
- Data processing hook : 45min
- Filters & interactions : 45min
- Polish & animations : 30min

---

## ✅ Success Criteria

- [ ] Treemap displays all tickers
- [ ] Size reflects article count
- [ ] Colors reflect sentiment
- [ ] Hover shows tooltip
- [ ] Click navigates to ticker
- [ ] Filters work (sector, time)
- [ ] Sentiment distribution accurate
- [ ] Time decay badges show freshness
- [ ] Smooth animations
- [ ] Responsive layout
- [ ] **Client says "WOW"** ✨

---

## 📈 Impact

### Before

- News as boring list
- No visual overview
- Hard to spot patterns
- Time to insight: **5-10 minutes**

### After

- ✅ **Visual spectacle**
- ✅ Instant pattern recognition
- ✅ Sentiment at-a-glance
- ✅ Time to insight: **10 seconds**
- ✅ **"Bloomberg Terminal" feel**

**Time Savings** : **95% reduction** (10min → 10sec)  
**Client Impression** : 🤯 Mind-blown

---

## 🔗 Integration Points

**Connected to** :
- ✅ useNews (data source)
- ✅ DrillDownContext (navigation)
- ✅ Command Palette (accessible via Ctrl+K)
- ✅ Tremor/Recharts (visualization)

**Ready for** :
- 🔜 Real-time updates (WebSocket)
- 🔜 Alert creation (click to set alert)
- 🔜 Export visualization (PNG/PDF)

---

## 🚀 Future Enhancements

### Phase 2
- 🔴 Real-time animation (pulsing colors)
- 📊 Historical sentiment trend (sparklines)
- 🎯 Custom watchlist overlay
- 🔔 Alert triggers from visualization
- 📱 Mobile gesture interactions
- 🎨 Theme customization
- 🤖 AI-powered pattern detection

---

**Signé** : ELENA-39  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 3-4h, +120 points
