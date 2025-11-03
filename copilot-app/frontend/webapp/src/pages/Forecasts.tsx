import { useEffect, useState } from 'react'
import { apiGet } from '../api/client'

type Row = {
  asset_type?: string
  ticker?: string
  commodity_name?: string
  category?: string
  horizon?: string
  final_score?: number
  direction?: string
  confidence?: number
  expected_return?: number
}

export default function Forecasts() {
  const [rows, setRows] = useState<Row[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    // The API returns { ok: boolean, data: { rows: [], count: number, asset_type: string } }
    apiGet<{ ok: boolean; data: { rows: Row[]; count: number; asset_type: string } | null; error?: string }>(`/forecasts`, { asset_type: 'all', horizon: 'all', sort_by: 'score' })
      .then((res) => {
        if (res.ok && res.data && res.data.rows) {
          setRows(res.data.rows);
        } else if (res.ok && res.data) {
          // Handle case where data exists but rows may be undefined
          setRows(res.data.rows || []);
        } else {
          setErr(res.error ?? 'Erreur inconnue');
        }
      })
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <h2>Forecasts</h2>
      {loading && <small>Chargement…</small>}
      {err && <small style={{ color: 'tomato' }}>{err}</small>}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>Type</th>
            <th>Symbole/Nom</th>
            <th>Horizon</th>
            <th>Score</th>
            <th>Dir</th>
            <th>Conf</th>
            <th>ER</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={[r.asset_type, r.ticker ?? r.commodity_name, r.horizon].filter(Boolean).join(':') || String(i)}>
              <td>{r.asset_type || ''}</td>
              <td>{r.ticker || r.commodity_name || ''}</td>
              <td>{r.horizon || ''}</td>
              <td>{r.final_score?.toFixed?.(2) ?? ''}</td>
              <td>{r.direction || ''}</td>
              <td>{r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : ''}</td>
              <td>{r.expected_return != null ? `${(r.expected_return * 100).toFixed(2)}%` : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
