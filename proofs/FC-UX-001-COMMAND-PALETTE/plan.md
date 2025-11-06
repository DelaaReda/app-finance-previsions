# FC-UX-001 : Command Palette (Ctrl+K) - Plan Détaillé

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Command Palette moderne pour navigation ultra-rapide  
**Points estimés** : +100

---

## 🎯 Objectif

Créer un **Command Palette** (comme VSCode, Linear, Notion) activé par `Ctrl+K` ou `/` pour :
- Navigation instantanée vers n'importe quelle page
- Recherche globale (tickers, forecasts, actions)
- Exécution de commandes (générer rapport, refresh data, etc.)
- **"Premium UX feel"** immédiat

**Vision** : L'utilisateur tape `Ctrl+K` → Recherche "AAPL" → Enter → Page ticker AAPL

---

## 💡 Pourquoi ça va ÉPATER le client

1. **UX Ultra-moderne** : VSCode/Linear/Notion style ✨
2. **Gain de temps massif** : Navigation en 2 secondes vs 30 secondes
3. **Sensation premium** : "Ce produit est professionnel"
4. **Découvrabilité** : Toutes les features accessibles via recherche
5. **Power user friendly** : Keyboard shortcuts

---

## 🏗️ Implementation

### 1. Command Palette Component

**Fichier** : `frontend/webapp/src/components/system/CommandPalette.tsx`

**Tech Stack** :
- **Mantine Spotlight** (built-in command palette component)
- **React hooks** (useState, useEffect, useMemo)
- **React Router** (useNavigate)

**Features** :
- ✅ Ouverture via `Ctrl+K` ou `Cmd+K` (Mac)
- ✅ Recherche fuzzy
- ✅ Catégories (Pages, Tickers, Actions, Recent)
- ✅ Icons par catégorie
- ✅ Navigation keyboard (↑↓, Enter, Esc)
- ✅ Highlights sur match

---

### 2. Command Registry

**Structure** :
```typescript
interface Command {
  id: string;
  label: string;
  description?: string;
  category: 'navigation' | 'ticker' | 'action' | 'recent';
  icon: React.ReactNode;
  action: () => void;
  keywords?: string[]; // For fuzzy search
}
```

**Command Types** :

#### A. Navigation Commands
```typescript
[
  { id: 'nav-dashboard', label: 'Dashboard', icon: <IconDashboard />, action: () => navigate('/') },
  { id: 'nav-forecasts', label: 'Forecasts', icon: <IconChartLine />, action: () => navigate('/forecasts') },
  { id: 'nav-news', label: 'News', icon: <IconNews />, action: () => navigate('/news') },
  // ... etc
]
```

#### B. Ticker Commands (Dynamic)
```typescript
// Generated from useForecasts
['AAPL', 'MSFT', 'NVDA', ...].map(ticker => ({
  id: `ticker-${ticker}`,
  label: `View ${ticker}`,
  icon: <IconChartCandle />,
  action: () => navigateToTicker(ticker),
  keywords: [ticker.toLowerCase()]
}))
```

#### C. Action Commands
```typescript
[
  { id: 'action-refresh', label: 'Refresh all data', icon: <IconRefresh />, action: refreshAll },
  { id: 'action-export', label: 'Export dashboard', icon: <IconDownload />, action: exportData },
  { id: 'action-theme', label: 'Toggle theme', icon: <IconMoon />, action: toggleTheme },
]
```

#### D. Recent Commands
```typescript
// Store last 5 visited pages in localStorage
const recent = useRecentPages(); // Custom hook
```

---

### 3. Keyboard Shortcut Hook

**Fichier** : `frontend/webapp/src/hooks/useCommandPalette.ts`

```typescript
export function useCommandPalette() {
  const [opened, setOpened] = useState(false);
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setOpened(true);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);
  
  return { opened, setOpened };
}
```

---

### 4. Integration with Drill-Down

**Connect with** :
- `useDrillDown` pour navigation contextuelle
- `useMarketContext` pour regime info
- `useForecasts` pour liste de tickers

---

## 🎨 User Experience

### Scenario 1 : Navigate to Page

1. User presses `Ctrl+K`
2. Palette opens (animated)
3. Types "fore"
4. Sees "Forecasts" highlighted
5. Presses Enter
6. → Navigates to /forecasts
7. Palette closes

**Time** : **2 seconds** vs 15 seconds (clicking through nav)

---

### Scenario 2 : Search Ticker

1. User presses `Ctrl+K`
2. Types "aapl"
3. Sees "View AAPL" in results
4. Presses Enter
5. → Navigates to /ticker/AAPL with search context
6. Sees forecasts for AAPL

**Time** : **3 seconds** vs 30 seconds (manual search)

---

### Scenario 3 : Execute Action

1. User presses `Ctrl+K`
2. Types "refresh"
3. Sees "Refresh all data"
4. Presses Enter
5. → Triggers data refresh
6. Notification appears
7. Palette closes

**Time** : **2 seconds** vs 20 seconds (clicking refresh buttons)

---

## 📊 Architecture

```
App
└── CommandPaletteProvider
    ├── useCommandPalette (keyboard listener)
    ├── CommandRegistry (all commands)
    ├── Mantine Spotlight
    └── Command Actions
        ├── Navigation (useNavigate)
        ├── DrillDown (useDrillDown)
        └── Actions (refresh, export, etc.)
```

---

## ⏱️ Timeline

**Estimation** : 2-3h

- CommandPalette component : 1h
- Command registry : 30min
- Keyboard shortcuts : 30min
- Integration & styling : 30min
- Testing : 30min

---

## ✅ Success Criteria

- [ ] Opens with `Ctrl+K` / `Cmd+K`
- [ ] Fuzzy search works
- [ ] Navigation commands work
- [ ] Ticker search works
- [ ] Action commands work
- [ ] Recent pages shown
- [ ] Keyboard navigation (↑↓)
- [ ] Esc closes palette
- [ ] Smooth animations
- [ ] Mobile-friendly (optional fallback)

---

## 📈 Impact

### Before

- Navigation via clicking through menus
- Time to page: **15-30 seconds**
- No global search
- No keyboard shortcuts
- Manual ticker search

### After

- ✅ `Ctrl+K` → **Instant access**
- ✅ Time to page: **2-3 seconds**
- ✅ Global search everything
- ✅ Power user shortcuts
- ✅ Instant ticker navigation
- ✅ **"Premium product" feel**

**Time Savings** : **90% reduction** (30s → 3s)  
**User Delight** : ⬆️⬆️⬆️ High

---

## 🚀 Future Enhancements

### Phase 2
- 🔍 Advanced filters (by date, score, etc.)
- 📊 Command analytics (most used)
- 🎨 Custom themes for palette
- 📱 Mobile gesture (swipe down)
- 🤖 LLM-powered suggestions
- 📌 Pin favorite commands
- ⌨️ Custom keyboard shortcuts

---

**Signé** : ELENA-39  
**Date** : 2025-11-06  
**Status** : Ready to implement  
**Estimation** : 2-3h, +100 points
