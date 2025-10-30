import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/api/client'

type ResultsResp = { mode: 'results'; rows: { date?: string; strategy?: string; equity?: number }[]; latest?: Record<string, number> }
type DetailsResp = { mode: 'details'; curve: { dates: string[]; values: number[] } }
type EmptyResp = { mode: 'empty' }

export default function Backtests() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => apiGet<ResultsResp | DetailsResp | EmptyResp>('/backtests').then(r => r.ok ? r.data : Promise.reject(r.error)),
    staleTime: 15_000,
  })

  return (
    <div>
      <h2>Backtests</h2>
      {isLoading && <small>Chargement…</small>}
      {error && <small style={{ color: 'tomato' }}>{String(error)}</small>}
      {data && data.mode === 'results' && (
        <div>
          <h4>Derniers points (results.parquet)</h4>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th>Date</th><th>Stratégie</th><th>Equity</th></tr></thead>
            <tbody>
              {data.rows.slice(-100).map((r, i) => (
                <tr key={i}><td>{r.date}</td><td>{r.strategy}</td><td>{r.equity?.toFixed?.(4)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && data.mode === 'details' && (
        <div>
          <h4>Courbe cumulée (details.parquet)</h4>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th>Date</th><th>Cumul</th></tr></thead>
            <tbody>
              {data.curve.dates.slice(-100).map((d, i) => (
                <tr key={i}><td>{d}</td><td>{(data.curve.values[i] * 100).toFixed(2)}%</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && data.mode === 'empty' && (
        <small>Aucun backtest disponible.</small>
      )}
    </div>
  )}

