import { RouterProvider, createBrowserRouter, createRoutesFromElements, Route, Outlet } from 'react-router-dom'
import { AppProviders } from './app/providers'
import GlobalErrorBoundary from './components/system/GlobalErrorBoundary'; // Global error boundary for stability
import AppShell from './layout/AppShell'; // Using the new MUI-based layout
import { DrillDownProvider } from './contexts/DrillDownContext'; // FC-INT-027: Intelligent drill-down navigation
import { CommandPalette } from './components/system/CommandPalette'; // FC-UX-001: Command Palette (Ctrl+K)
import { useCommandPalette } from './hooks/useCommandPalette'; // FC-UX-001: Command Palette hook

// Pages existantes
import Dashboard from './pages/Dashboard'
import ForecastsMinimal from './pages/ForecastsMinimal'
import LLMJudge from './pages/LLMJudge'
import Backtests from './pages/Backtests'
import CompareStrategies from './pages/CompareStrategies'
import DashboardsPage from './pages/Dashboards'

// Nouvelles pages selon VISION
import Macro from './pages/Macro'
import Stocks from './pages/Stocks'
import News from './pages/News'
import NewsSignalRadar from './pages/NewsSignalRadar' // FC-UX-002: News Signal Radar (Treemap visualization)
import Copilot from './pages/Copilot'
import TickerDetail from './pages/TickerDetail' // FC-INT-027: Replaces TickerSheet with intelligent drill-down
import MarketBrief from './pages/MarketBrief'
import Portfolios from './pages/Portfolios' // API-PORTFOLIO-002: Portfolio/Watchlist management
import TestSimple from './pages/TestSimple'

// AppContent wrapper with Command Palette
function AppContent() {
  const { opened, close } = useCommandPalette();
  
  return (
    <>
      <CommandPalette opened={opened} close={close} />
      <Outlet />
    </>
  );
}

// Create router with error boundary wrapper, drill-down context, and command palette
const router = createBrowserRouter(createRoutesFromElements(
  <Route element={
    <GlobalErrorBoundary>
      <DrillDownProvider>
        <AppShell>
          <AppContent />
        </AppShell>
      </DrillDownProvider>
    </GlobalErrorBoundary>
  }>
    <Route index element={<Dashboard />} />
    <Route path="/brief" element={<MarketBrief />} />
    <Route path="/macro" element={<Macro />} />
    <Route path="/stocks" element={<Stocks />} />
    <Route path="/news" element={<News />} />
    <Route path="/news/radar" element={<NewsSignalRadar />} /> {/* FC-UX-002: News Signal Radar */}
    <Route path="/copilot" element={<Copilot />} />
    <Route path="/portfolios" element={<Portfolios />} /> {/* API-PORTFOLIO-002: Portfolio management */}
    <Route path="/ticker/:ticker" element={<TickerDetail />} /> {/* FC-INT-027: Intelligent drill-down */}
    <Route path="/forecasts" element={<ForecastsMinimal />} />
    <Route path="/test" element={<TestSimple />} />
    <Route path="/backtests" element={<Backtests />} />
    <Route path="/compare" element={<CompareStrategies />} />
    <Route path="/dashboards/:slug?" element={<DashboardsPage />} />
    <Route path="/judge" element={<LLMJudge />} />
  </Route>
));

export default function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  )
}
