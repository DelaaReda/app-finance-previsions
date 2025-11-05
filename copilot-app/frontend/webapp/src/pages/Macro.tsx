// Page Macro - Pilier 1: Données macro (FRED, VIX, cycles)
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMacroSeries } from '../services/macro.service'
import { safeMap, safeLength } from '@/utils/safeAccess'
import MiniLineChart from '../components/charts/MiniLineChart'

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
    enabled: safeLength(selectedSeries) > 0,
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
          {safeMap(MACRO_SERIES, series => (
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
      {data && Array.isArray(data) && data.length > 0 && (
        <div>
          {data.map((seriesObj, index) => {
            // Render current values as a single data point or as a chart if historical data becomes available
            const seriesEntries = Object.entries(seriesObj || {});
            
            return seriesEntries.map(([key, value]) => {
              const prettyKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
              
              // For now, create a minimal chart with just the current value
              // In the future, when historical data is available, this will show trends
              const currentDataPoint = [
                { date: new Date().toISOString(), value: typeof value === 'number' ? value : 0 }
              ];
              
              return (
                <div key={`${key}-${index}`} style={{ background: 'white', padding: 24, borderRadius: 8, marginBottom: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
                  <h3 style={{ marginBottom: 8, fontSize: 18, fontWeight: 600 }}>{prettyKey}: {typeof value === 'number' ? value.toFixed(2) : value}</h3>
                  <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#4a9eff' }}>
                        {typeof value === 'number' ? value.toFixed(2) : value}
                      </div>
                      <div style={{ fontSize: 12, color: '#888', marginTop: 8 }}>
                        Valeur actuelle • Aucune série historique disponible
                      </div>
                    </div>
                  </div>
                </div>
              );
            });
          })}
        </div>
      )}
      {data && Array.isArray(data) && data.length === 0 && (
        <div style={{ color: '#888', fontStyle: 'italic', textAlign: 'center', padding: 20 }}>
          Aucune donnée macro disponible pour le moment.
        </div>
      )}
      {!data && (
        <div style={{ color: '#888', fontStyle: 'italic', textAlign: 'center', padding: 20 }}>
          Chargement des données macro...
        </div>
      )}
    </div>
  )
}
