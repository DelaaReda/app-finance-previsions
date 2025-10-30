import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/api/client'

type Kpis = {
  last_forecast_dt?: string | null
  forecasts_count?: number
  tickers?: number
  horizons?: string[]
  last_macro_dt?: string | null
  last_quality_dt?: string | null
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard-kpis'],
    queryFn: () => apiGet<Kpis>('/dashboard/kpis').then(r => r.ok ? r.data : Promise.reject(r.error)),
    staleTime: 15_000,
  })

  return (
    <div>
      <h2>Dashboard</h2>
      {isLoading && <small>Chargement…</small>}
      {error && <small style={{ color: 'tomato' }}>{String(error)}</small>}
      {data && (
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
          <Card title="Dernière partition Forecasts" value={data.last_forecast_dt || '—'} />
          <Card title="# Prévisions" value={data.forecasts_count ?? 0} />
          <Card title="# Tickers" value={data.tickers ?? 0} />
          <Card title="Horizons" value={(data.horizons || []).join(', ') || '—'} />
          <Card title="Dernière Macro" value={data.last_macro_dt || '—'} />
          <Card title="Fraîcheur Qualité" value={data.last_quality_dt || '—'} />
        </div>
      )}
    </div>
  )
}

function Card({ title, value }: { title: string; value: any }) {
  return (
    <div style={{ border: '1px solid #444', borderRadius: 8, padding: 12 }}>
      <div style={{ fontSize: 12, color: '#999' }}>{title}</div>
      <div style={{ fontSize: 22, fontWeight: 600 }}>{String(value)}</div>
    </div>
  )
}

