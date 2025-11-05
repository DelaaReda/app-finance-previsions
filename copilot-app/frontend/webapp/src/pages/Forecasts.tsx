import { useEffect, useState } from 'react'
import { apiGet } from '../api/client'
import { FreshnessBadge } from '../components/ui/FreshnessBadge'
import { EmptyState } from '../components/ui/EmptyState'
import { safeGetArray, hasSafeArray, safeMap } from '../utils/safeAccess'

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

type ApiForecastsPayload = {
  rows: Row[]
  count?: number
  asset_type?: string
  freshness?: string
  last_update?: string
}

async function fetchForecastsFromApi(): Promise<ApiForecastsPayload> {
  const res = await apiGet<ApiForecastsPayload>(`/forecasts`, { asset_type: 'all', horizon: 'all', sort_by: 'score' })
  const data = (res as any).data as ApiForecastsPayload | undefined
  if (res.ok && data) {
    const safeRows = Array.isArray(data.rows) ? data.rows : []
    return { ...data, rows: safeRows }
  }

  return { rows: [] }
}

export default function Forecasts() {
  const [rawData, setRawData] = useState<ApiForecastsPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    const load = async () => {
      setLoading(true)
      try {
        const payload = await fetchForecastsFromApi()
        if (mounted) setRawData(payload)
      } catch (e: any) {
        if (mounted) setErr(e?.message || 'Erreur de chargement')
      } finally {
        if (mounted) setLoading(false)
      }
    }

    load()
    return () => { mounted = false }
  }, [])

  const rows = rawData?.rows ?? []
  const freshness = rawData?.freshness ?? rawData?.last_update ?? null

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2>Forecasts</h2>
        <FreshnessBadge 
          freshness={freshness} 
          stale={freshness ? new Date().getTime() - new Date(freshness).getTime() > 3600000 : false} 
        />
      </div>

      {loading && <small>Chargement…</small>}
      {err && <small style={{ color: 'tomato' }}>{err}</small>}

      {!loading && !err && rows.length === 0 && (
        <>
          <EmptyState
            title="Aucune prévision disponible"
            hint={freshness ? `Dernière mise à jour: ${new Date(freshness).toLocaleString()}` : "Le modèle calcule en arrière-plan…"}
          />
          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button
              onClick={async () => {
                setLoading(true)
                setErr(null)
                try {
                  const payload = await fetchForecastsFromApi()
                  setRawData(payload)
                } catch (e: any) {
                  setErr(e?.message || 'Erreur de chargement')
                } finally {
                  setLoading(false)
                }
              }}
              disabled={loading}
            >
              {loading ? 'Chargement…' : 'Rafraîchir'}
            </button>
            <button onClick={() => window.location.reload()} style={{ background: 'transparent', border: '1px solid #ddd', padding: '6px 10px' }}>
              Forcer rechargement
            </button>
          </div>
        </>
      )}

      {!loading && !err && hasSafeArray({ rows }, 'rows') && (
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
            {safeMap(safeGetArray({ rows }, 'rows'), (r: Row, i: number) => (
              <tr key={[r.asset_type, r.ticker ?? r.commodity_name, r.horizon].filter(Boolean).join(':') || String(i)}>
                <td>{r.asset_type || ''}</td>
                <td>{r.ticker || r.commodity_name || ''}</td>
                <td>{r.horizon || ''}</td>
                <td>{r.final_score?.toFixed?.(2) ?? '-'}</td>
                <td>{r.direction || '-'}</td>
                <td>{r.confidence != null ? `${(r.confidence * 100).toFixed(0)}%` : '-'}</td>
                <td>{r.expected_return != null ? `${(r.expected_return * 100).toFixed(2)}%` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
