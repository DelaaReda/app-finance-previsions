import { RouterProvider, createBrowserRouter, createRoutesFromElements, Route, Outlet, Link } from 'react-router-dom'
import { AppProviders } from './app/providers'

// Pages existantes
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import LLMJudge from './pages/LLMJudge'
import Backtests from './pages/Backtests'

// Nouvelles pages selon VISION
import Macro from './pages/Macro'
import Stocks from './pages/Stocks'
import News from './pages/News'
import Copilot from './pages/Copilot'
import TickerSheet from './pages/TickerSheet'
import MarketBrief from './pages/MarketBrief'

// Layout avec navigation pour l'application
function AppLayout() {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* Sidebar Navigation */}
      <nav style={{
        width: 240,
        background: '#1a1a1a',
        padding: 20,
        color: 'white',
        position: 'fixed',
        height: '100vh',
        overflowY: 'auto'
      }}>
        <h1 style={{ fontSize: 20, marginBottom: 24, fontWeight: 600 }}>
          💼 Finance Copilot
        </h1>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <NavSection title="📊 Vue d'ensemble">
            <NavLink to="/">Dashboard</NavLink>
            <NavLink to="/brief">Market Brief</NavLink>
          </NavSection>
          
          <NavSection title="🔬 5 Piliers">
            <NavLink to="/macro">1. Macro</NavLink>
            <NavLink to="/stocks">2. Stocks</NavLink>
            <NavLink to="/news">3. News</NavLink>
            <NavLink to="/copilot">4. Copilot LLM</NavLink>
          </NavSection>
          
          <NavSection title="📈 Analyse">
            <NavLink to="/forecasts">Prévisions</NavLink>
            <NavLink to="/backtests">Backtests</NavLink>
          </NavSection>
          
          <NavSection title="🛠️ Outils">
            <NavLink to="/judge">LLM Judge</NavLink>
          </NavSection>
        </div>
      </nav>

      {/* Main Content - contenu des routes */}
      <main style={{ marginLeft: 240, flex: 1, padding: 32, background: '#f5f5f5' }}>
        <Outlet />
      </main>
    </div>
  );
}

// Create router
const router = createBrowserRouter(createRoutesFromElements(
  <Route element={<AppLayout />}>
    <Route index element={<Dashboard />} />
    <Route path="/brief" element={<MarketBrief />} />
    <Route path="/macro" element={<Macro />} />
    <Route path="/stocks" element={<Stocks />} />
    <Route path="/news" element={<News />} />
    <Route path="/copilot" element={<Copilot />} />
    <Route path="/ticker/:symbol" element={<TickerSheet />} />
    <Route path="/forecasts" element={<Forecasts />} />
    <Route path="/backtests" element={<Backtests />} />
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

// Helper Components
function NavSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', opacity: 0.6, marginBottom: 8, fontWeight: 600 }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {children}
      </div>
    </div>
  )
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      style={{
        padding: '8px 12px',
        borderRadius: 6,
        textDecoration: 'none',
        color: 'white',
        fontSize: 14,
        transition: 'all 0.2s',
      }}
      onMouseEnter={(e) => e.currentTarget.style.background = '#333'}
      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
    >
      {children}
    </Link>
  )
}
