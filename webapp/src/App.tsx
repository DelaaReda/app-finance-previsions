import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import Forecasts from './pages/Forecasts'
import LLMJudge from './pages/LLMJudge'
import AppProviders from './app/providers'

export default function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <div style={{ padding: 16, fontFamily: 'system-ui, sans-serif' }}>
          <h1>Finance Agent — React UI</h1>
          <nav style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <Link to="/">Forecasts</Link>
            <Link to="/judge">LLM Judge</Link>
          </nav>
          <Routes>
            <Route path="/" element={<Forecasts />} />
            <Route path="/judge" element={<LLMJudge />} />
          </Routes>
        </div>
      </BrowserRouter>
    </AppProviders>
  )
}
