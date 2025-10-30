/**
 * Application principale React
 * Migration Dash/Streamlit → React
 * Basé sur VISION: 5 piliers + Dashboard + Copilot
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppProviders from './app/providers'
import Header from './components/layout/Header'
import Footer from './components/layout/Footer'

// Pages existantes
import Dashboard from './pages/Dashboard'
import Forecasts from './pages/Forecasts'
import LLMJudge from './pages/LLMJudge'
import Backtests from './pages/Backtests'

// Nouvelles pages (à créer)
import Macro from './pages/Macro'
import Stocks from './pages/Stocks'
import News from './pages/News'
import Copilot from './pages/Copilot'
import MarketBrief from './pages/MarketBrief'
import TickerSheet from './pages/TickerSheet'

export default function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          backgroundColor: '#0a0a0a',
          color: '#e0e0e0',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}>
          <Header />
          
          <main style={{
            flex: 1,
            padding: '2rem',
            maxWidth: '1400px',
            width: '100%',
            margin: '0 auto',
          }}>
            <Routes>
              {/* Dashboard principal */}
              <Route path="/" element={<Dashboard />} />
              
              {/* 5 Piliers selon VISION */}
              <Route path="/macro" element={<Macro />} />
              <Route path="/stocks" element={<Stocks />} />
              <Route path="/stocks/:ticker" element={<TickerSheet />} />
              <Route path="/news" element={<News />} />
              <Route path="/copilot" element={<Copilot />} />
              
              {/* Market Brief */}
              <Route path="/brief" element={<MarketBrief />} />
              
              {/* Pages existantes */}
              <Route path="/forecasts" element={<Forecasts />} />
              <Route path="/backtests" element={<Backtests />} />
              <Route path="/judge" element={<LLMJudge />} />
            </Routes>
          </main>
          
          <Footer />
        </div>
      </BrowserRouter>
    </AppProviders>
  )
}
