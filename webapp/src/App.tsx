import { useState } from 'react'
import Forecasts from './pages/Forecasts'
import LLMJudge from './pages/LLMJudge'

export default function App() {
  const [tab, setTab] = useState<'forecasts' | 'judge'>('forecasts')
  return (
    <div style={{ padding: 16, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Finance Agent — React UI</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button onClick={() => setTab('forecasts')} disabled={tab === 'forecasts'}>Forecasts</button>
        <button onClick={() => setTab('judge')} disabled={tab === 'judge'}>LLM Judge</button>
      </div>
      {tab === 'forecasts' ? <Forecasts /> : <LLMJudge />}
    </div>
  )
}

