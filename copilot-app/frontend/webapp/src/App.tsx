import { RouterProvider, createBrowserRouter, createRoutesFromElements, Route, Outlet } from 'react-router-dom'
import { AppProviders } from './app/providers'
import GlobalErrorBoundary from './components/system/GlobalErrorBoundary'; // Global error boundary for stability
import AppShell from './layout/AppShell'; // Using the new MUI-based layout

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
import Copilot from './pages/Copilot'
import TickerSheet from './pages/TickerSheet'
import MarketBrief from './pages/MarketBrief'
import TestSimple from './pages/TestSimple'

// Create router with error boundary wrapper
const router = createBrowserRouter(createRoutesFromElements(
  <Route element={
    <GlobalErrorBoundary>
      <AppShell>
        <Outlet />
      </AppShell>
    </GlobalErrorBoundary>
  }>
    <Route index element={<Dashboard />} />
    <Route path="/brief" element={<MarketBrief />} />
    <Route path="/macro" element={<Macro />} />
    <Route path="/stocks" element={<Stocks />} />
    <Route path="/news" element={<News />} />
    <Route path="/copilot" element={<Copilot />} />
    <Route path="/ticker/:symbol" element={<TickerSheet />} />
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
