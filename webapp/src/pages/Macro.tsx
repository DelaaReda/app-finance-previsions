// Page Macro - Pilier 1: Données macro (FRED, VIX, cycles)
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMacroSeries } from '../services/macro.service'

const MACRO_SERIES = [
  { id: 'CPIAUCSL', name: 'CPI (Inflation)' },
  { id: 'VIXCLS', name: 'VIX (Volatilité)' },
  { id: 'T10Y2Y', name: 'Yield Curve 10Y-2Y' },
  { id: 'UNRATE', name: 'Unemployment Rate' },
]

export default function Macro() {
  const [selectedSeries, setSelectedSeries] = useState<string[]>(['CPIAUCSL', 'VIXCLS'])
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['macro-series', selectedSeries],
    queryFn: () => fetchMacroSeries(selectedSeries, '2019-01-01').then(r => r.ok ? r.data : Promise.reject(r.error)),
    enabled: selectedSeries.length > 0,
    staleTime: 3600000, // 1h
  })

  return (
    <div>
      <h2 style={{ marginBottom: 24, fontSize: 28, fontWeight: 600 }}>
        📈 Macro (Pilier 1)
      </h2>
      
      <p style={{ marginBottom: 24, color: '#666' }}>
        Données macroéconomiques clés (FRED, VIX, cycles économiques)
      </p>

      {/* Sélecteur de séries */}
      <div style={{ marginBottom: 32, background: 'white', padding: 20, borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 600 }}>Séries à afficher</h3>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {MACRO_SERIES.map(series => (
            <label key={series.id} style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={selectedSeries.includes(series.id)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setSelectedSeries([...selectedSeries, series.id])
                  } else {
                    setSelectedSeries(selectedSeries.filter(s => s !== series.id))
                  }
                }}
              />
              <span>{series.name}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Chargement et erreurs */}
      {isLoading && <div style={{ textAlign: 'center', padding: 40 }}>Chargement des données macro...</div>}
      {error && <div style={{ color: 'tomato', background: '#fff', padding: 20, borderRadius: 8 }}>Erreur: {String(error)}</div>}

      {/* Graphiques */}
      {data && Object.entries(data).map(([seriesId, seriesData]) => {
        const series = MACRO_SERIES.find(s => s.id === seriesId)
        return (
          <div key={seriesId} style={{ background: 'white', padding: 24, borderRadius: 8, marginBottom: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h3 style={{ marginBottom: 8, fontSize: 18, fontWeight: 600 }}>{series?.name || seriesId}</h3>
