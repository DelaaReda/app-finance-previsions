import { useState } from 'react'
import { apiPost } from '../api/client'

export default function LLMJudge() {
  const [model, setModel] = useState('deepseek-ai/DeepSeek-V3-0324-Turbo')
  const [tickers, setTickers] = useState('AAPL,MSFT,NGD.TO')
  const [busy, setBusy] = useState(false)
  const [out, setOut] = useState('')
  const [rowsCount, setRowsCount] = useState<number | null>(null)

  const run = async () => {
    setBusy(true)
    setOut('(running…)')
    try {
      const res = await apiPost<{ stdout?: { context?: string; forecast?: string }; rows?: any[] }>(
        '/api/llm/judge/run',
        { model, max_er: 0.08, min_conf: 0.6, tickers }
      )
      if (res.ok && res.data) {
        const ctx = res.data.stdout?.context ?? '—'
        const fc = res.data.stdout?.forecast ?? '—'
        const rows = Array.isArray(res.data.rows) ? res.data.rows : []
        setRowsCount(rows.length)
        setOut([ctx, '----', fc].join('\n'))
      } else {
        setRowsCount(null)
        setOut('Erreur: ' + (res.error ?? 'Réponse invalide'))
      }
    } catch (e: any) {
      setRowsCount(null)
      setOut('Erreur: ' + (e?.message ?? String(e)))
    }
    setBusy(false)
  }

  return (
    <div data-testid="judge-root" style={{ display: 'grid', gap: 12 }}>
      <h2>LLM Judge</h2>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <label>Model</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} style={{ minWidth: 360 }} />
        <label>Tickers</label>
        <input value={tickers} onChange={(e) => setTickers(e.target.value)} style={{ minWidth: 240 }} />
        <button disabled={busy} onClick={run}>Run</button>
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', color: '#888' }}>
        <span>Rows:</span>
        <strong>{rowsCount ?? '—'}</strong>
      </div>
      <pre style={{ whiteSpace: 'pre-wrap', maxHeight: '40vh', overflowY: 'auto', marginTop: 12 }}>{out || 'Cliquez sur Run pour exécuter le juge LLM.'}</pre>
    </div>
  )
}
