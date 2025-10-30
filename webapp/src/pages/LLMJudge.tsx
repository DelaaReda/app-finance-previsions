import { useState } from 'react'
import { apiPost } from '../api/client'

export default function LLMJudge() {
  const [model, setModel] = useState('deepseek-ai/DeepSeek-V3-0324-Turbo')
  const [tickers, setTickers] = useState('AAPL,MSFT,NGD.TO')
  const [busy, setBusy] = useState(false)
  const [out, setOut] = useState('')

  const run = async () => {
    setBusy(true)
    setOut('(running…)')
    const res = await apiPost<{ stdout: { context: string; forecast: string }; rows: any[] }>(
      '/llm/judge/run',
      { model, max_er: 0.08, min_conf: 0.6, tickers }
    )
    if (res.ok) {
      setOut([res.data.stdout.context, '----', res.data.stdout.forecast].join('\n'))
    } else {
      setOut('Erreur: ' + res.error)
    }
    setBusy(false)
  }

  return (
    <div>
      <h2>LLM Judge</h2>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <label>Model</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} style={{ minWidth: 360 }} />
        <label>Tickers</label>
        <input value={tickers} onChange={(e) => setTickers(e.target.value)} style={{ minWidth: 240 }} />
        <button disabled={busy} onClick={run}>Run</button>
      </div>
      <pre style={{ whiteSpace: 'pre-wrap', maxHeight: '40vh', overflowY: 'auto', marginTop: 12 }}>{out}</pre>
    </div>
  )
}

