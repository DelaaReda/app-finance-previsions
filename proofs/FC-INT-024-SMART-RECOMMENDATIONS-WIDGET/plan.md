# FC-INT-024 : SmartRecommendationsWidget - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Widget frontend pour afficher les recommandations intelligentes  
**Points estimés** : +70

---

## 🎯 Objectif

Créer le **SmartRecommendationsWidget** - Widget frontend qui affiche les top 3 recommandations quotidiennes du RecommendationsService avec drill-down navigation.

---

## 📊 Architecture

### Data Flow

```
SmartRecommendationsWidget
     ↓
useRecommendations() hook
     ↓
GET /api/recommendations/daily
     ↓
RecommendationsService (backend)
     ↓
Display recommendations
```

---

## 🎨 Component Structure

### Main Widget

```tsx
<SmartRecommendationsWidget>
  <Header title="Today's Smart Picks" refresh badge />
  <RecommendationsList>
    <RecommendationCard ticker action score reasoning catalysts risk />
    <RecommendationCard ... />
    <RecommendationCard ... />
  </RecommendationsList>
  <Footer lastUpdate validUntil />
</SmartRecommendationsWidget>
```

---

## 📁 Files to Create

1. **`hooks/useRecommendations.ts`** (30 lines)
2. **`components/recommendations/RecommendationCard.tsx`** (120 lines)
3. **`components/widgets/SmartRecommendationsWidget.tsx`** (150 lines)

---

## 🎯 User Experience

### Normal Display

```
┌────────────────────────────────────┐
│ 📈 Today's Smart Picks  [Refresh]  │
├────────────────────────────────────┤
│ ┌────────────────────────────────┐ │
│ │ AAPL           BUY    Score 87%│ │
│ │ ⭐⭐⭐⭐⭐              MEDIUM  │ │
│ │ Strong momentum post-earnings  │ │
│ │ • Q4 earnings beat             │ │
│ │ • iPhone sales growth          │ │
│ │ [View Details →]               │ │
│ └────────────────────────────────┘ │
│ ┌────────────────────────────────┐ │
│ │ MSFT           BUY    Score 84%│ │
│ └────────────────────────────────┘ │
├────────────────────────────────────┤
│ Updated 2h ago • Valid until 6pm   │
└────────────────────────────────────┘
```

---

## ⏱️ Timeline

**Estimation** : 1-1.5h

- Hook (useRecommendations) : 15 min
- RecommendationCard : 30 min
- SmartRecommendationsWidget : 30 min
- Styling + responsive : 15 min

---

**Signé** : ELENA-39  
**Date** : 2025-11-06  
**Status** : Ready to implement
