# API-PORTFOLIO-002 : Frontend Integration - Plan

**Agent** : ELENA-INTEGRATION-UX-ENGINEER-BLACKWIDOW-39  
**Date** : 2025-11-06  
**Mission** : Complete frontend integration for Portfolio/Watchlist management  
**Points estimés** : +60  
**Priorité** : 🔥 HIGH (complete the portfolio feature end-to-end)

---

## 🎯 Objectif

Intégrer complètement les portfolios/watchlists dans le frontend :
- ✅ Hook React Query pour consommer l'API
- ✅ Widget de gestion (create, edit, delete)
- ✅ Intégration Command Palette
- ✅ Filtre Dashboard par portfolio

---

## 🏗️ Architecture Frontend

### 1. **Hook React Query** 

**File** : `frontend/webapp/src/hooks/usePortfolios.ts`

**Hooks** :
```typescript
usePortfolios() // List all portfolios
usePortfolio(id) // Get single portfolio
useCreatePortfolio() // Mutation: create
useUpdatePortfolio() // Mutation: update
useDeletePortfolio() // Mutation: delete
useAddTickers() // Mutation: add tickers
useRemoveTicker() // Mutation: remove ticker
usePortfolioPerformance(id) // Get performance
```

**Features** :
- React Query caching (5min stale time)
- Optimistic updates
- Auto-invalidation on mutations
- Error handling

---

### 2. **Portfolio Manager Widget**

**File** : `frontend/webapp/src/components/widgets/PortfolioManagerWidget.tsx`

**Features** :
- 📋 **List View** : All portfolios in cards/table
- ➕ **Create Modal** : Form to create new portfolio
- ✏️ **Edit Modal** : Update name/description/tickers
- 🗑️ **Delete Confirmation** : Safe delete with modal
- 🏷️ **Ticker Chips** : Visual ticker list with remove button
- ➕ **Add Tickers** : Search + add tickers to portfolio
- 📊 **Stats** : Count, created/updated dates

**UI Components** (Mantine) :
- `Card` for portfolio items
- `Modal` for create/edit
- `Button`, `TextInput`, `Textarea`
- `Badge` for tickers
- `ActionIcon` for actions
- `Menu` for dropdown actions

---

### 3. **Command Palette Integration**

**File** : `frontend/webapp/src/components/system/CommandPalette.tsx` (modify)

**New Actions** :
```typescript
{
  id: 'portfolio-tech',
  label: 'Show Tech Watchlist',
  icon: IconBriefcase,
  action: () => navigateToPortfolio('tech-id')
}
```

**Dynamic Actions** :
- Load portfolios from `usePortfolios()`
- Generate action per portfolio
- Navigate to filtered view or portfolio detail page

---

### 4. **Dashboard Filter by Portfolio**

**File** : `frontend/webapp/src/pages/Dashboard.tsx` (modify)

**Features** :
- `Select` dropdown in header : "Filter by Portfolio"
- When selected → filter forecasts/news by portfolio tickers
- "All Tickers" option (default)
- Badge showing active filter

**Implementation** :
```typescript
const [selectedPortfolioId, setSelectedPortfolioId] = useState(null)
const portfolio = usePortfolio(selectedPortfolioId)
const filteredTickers = portfolio ? portfolio.tickers : allTickers
// Pass filteredTickers to widgets
```

---

## 📊 User Flows

### Create Portfolio Flow
1. User clicks "Create Watchlist" button
2. Modal opens with form (name, description, tickers)
3. User fills form + selects tickers
4. Submit → API call → success toast
5. List refreshes with new portfolio

### Edit Portfolio Flow
1. User clicks "Edit" icon on portfolio card
2. Modal opens pre-filled with current data
3. User modifies fields
4. Submit → API call → optimistic update
5. Card updates immediately

### Delete Portfolio Flow
1. User clicks "Delete" icon
2. Confirmation modal appears
3. User confirms → API call
4. Portfolio removed from list

### Dashboard Filter Flow
1. User selects portfolio from dropdown
2. Dashboard widgets filter to show only portfolio tickers
3. Badge shows active filter
4. "Clear filter" button to reset

---

## 🎯 Components Structure

```
components/
├── widgets/
│   └── PortfolioManagerWidget.tsx (NEW, ~400 lines)
├── portfolios/ (NEW)
│   ├── PortfolioCard.tsx (display portfolio)
│   ├── PortfolioCreateModal.tsx (create form)
│   ├── PortfolioEditModal.tsx (edit form)
│   ├── PortfolioDeleteModal.tsx (confirm delete)
│   └── TickerSelect.tsx (ticker search + multi-select)
└── system/
    └── CommandPalette.tsx (MODIFY - add portfolio actions)

hooks/
└── usePortfolios.ts (NEW, ~200 lines)

pages/
└── Dashboard.tsx (MODIFY - add portfolio filter)
```

---

## 🧪 Testing Plan

### Manual Tests
1. **Create** : Create "Tech" portfolio with AAPL, MSFT, GOOGL ✅
2. **List** : View all portfolios in widget ✅
3. **Edit** : Rename to "Tech Giants", add NVDA ✅
4. **Add Ticker** : Add AMD ✅
5. **Remove Ticker** : Remove GOOGL ✅
6. **Delete** : Delete portfolio ✅
7. **Command Palette** : Ctrl+K → "Show Tech Watchlist" ✅
8. **Dashboard Filter** : Select "Tech" → only Tech tickers shown ✅

### Edge Cases
- Empty portfolios (no tickers)
- Duplicate ticker prevention
- Network errors (toast messages)
- Optimistic updates rollback

---

## 📈 Impact

### User Experience
- 🎯 **Quick access** : Organize 100+ tickers into manageable groups
- 🚀 **Fast switching** : Command Palette instant navigation
- 📊 **Focused analysis** : Dashboard filter eliminates noise
- 💾 **Persistent** : Watchlists saved across sessions

### Technical
- ✅ **End-to-end feature** : Backend + Frontend complete
- ✅ **Best practices** : React Query, Mantine UI, TypeScript
- ✅ **Reusable** : Components can be used in other pages
- ✅ **Extensible** : Ready for performance charts, comparisons

---

## 🎯 Timeline

**Estimation** : 2-3h

- `usePortfolios.ts` hook : 45min
- `PortfolioManagerWidget.tsx` : 1h
- Command Palette integration : 30min
- Dashboard filter : 30min
- Testing : 30min

**Start** : NOW

---

**Signé** : ELENA-39  
**Status** : Starting implementation
