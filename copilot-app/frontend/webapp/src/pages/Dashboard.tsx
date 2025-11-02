// Dashboard principal - Vue d'ensemble avec Top 3 Signaux/Risques

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/services/api'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import TopSignals from '@/components/signals/TopSignals'
import TopRisks from '@/components/signals/TopRisks'

type DashboardData = {
  last_forecast_dt?: string | null
  forecasts_count?: number
  tickers?: number
  horizons?: string[]
  last_macro_dt?: string | null
  last_quality_dt?: string | null
}

export default function Dashboard() {
  const [sectors, setSectors] = useState<string[]>([])
  const [horizons, setHorizons] = useState<string[]>([])
  const [themes, setThemes] = useState<string[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  
  // Sector options
  const sectorOptions = ["Technology", "Healthcare", "Financials", "Consumer", "Industrials", "Energy", "Utilities", "Real Estate"]
  // Horizon options
  const horizonOptions = ["short", "medium", "long"]
  // Theme options
  const themeOptions = ["growth", "value", "momentum", "dividend", "quality"]

  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiGet<DashboardData>('/dashboard/kpis')
      .then(r => r.ok ? r.data : Promise.reject(r.error)),
    staleTime: 15_000,
  })

  const handleSectorChange = (sector: string) => {
    setSectors(prev => 
      prev.includes(sector) 
        ? prev.filter(s => s !== sector) 
        : [...prev, sector]
    )
  }

  const handleHorizonChange = (horizon: string) => {
    setHorizons(prev => 
      prev.includes(horizon) 
        ? prev.filter(h => h !== horizon) 
        : [...prev, horizon]
    )
  }

  const handleThemeChange = (theme: string) => {
    setThemes(prev => 
      prev.includes(theme) 
        ? prev.filter(t => t !== theme) 
        : [...prev, theme]
    )
  }

  const handleTickerChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setTickers(value ? value.split(',').map(t => t.trim().toUpperCase()) : [])
  }

  return (
    <MainLayout>
      <div style={styles.container}>
        <h2 style={styles.pageTitle}>Dashboard - Vue d'ensemble</h2>
        
        {/* Filtres */}
        <Card title="Filtres (Secteur, Horizon, Thème)">
          <div style={styles.filtersContainer}>
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Secteurs:</label>
              <div style={styles.checkboxGroup}>
                {sectorOptions.map(sector => (
                  <label key={sector} style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={sectors.includes(sector)}
                      onChange={() => handleSectorChange(sector)}
                      style={styles.checkbox}
                    />
                    {sector}
                  </label>
                ))}
              </div>
            </div>
            
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Horizons:</label>
              <div style={styles.checkboxGroup}>
                {horizonOptions.map(horizon => (
                  <label key={horizon} style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={horizons.includes(horizon)}
                      onChange={() => handleHorizonChange(horizon)}
                      style={styles.checkbox}
                    />
                    {horizon}
                  </label>
                ))}
              </div>
            </div>
            
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Thèmes:</label>
              <div style={styles.checkboxGroup}>
                {themeOptions.map(theme => (
                  <label key={theme} style={styles.checkboxLabel}>
                    <input
                      type="checkbox"
                      checked={themes.includes(theme)}
                      onChange={() => handleThemeChange(theme)}
                      style={styles.checkbox}
                    />
                    {theme}
                  </label>
                ))}
              </div>
            </div>
            
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>Tickers (séparés par des virgules):</label>
              <input
                type="text"
                value={tickers.join(',')}
                onChange={handleTickerChange}
                placeholder="ex: AAPL,MSFT,GOOGL"
                style={styles.textInput}
              />
            </div>
            
            {(sectors.length > 0 || horizons.length > 0 || themes.length > 0 || tickers.length > 0) && (
              <div style={styles.activeFilters}>
                <small>Filtres actifs:</small>
                {sectors.length > 0 && <span style={styles.filterBadge}>Secteurs: {sectors.join(', ')}</span>}
                {horizons.length > 0 && <span style={styles.filterBadge}>Horizons: {horizons.join(', ')}</span>}
                {themes.length > 0 && <span style={styles.filterBadge}>Thèmes: {themes.join(', ')}</span>}
                {tickers.length > 0 && <span style={styles.filterBadge}>Tickers: {tickers.join(', ')}</span>}
              </div>
            )}
          </div>
        </Card>
        
        {/* KPIs Grid */}
        <div style={styles.kpisGrid}>
          <Card title="Dernière prévision">
            <div style={styles.kpiValue}>{data?.last_forecast_dt || '—'}</div>
          </Card>
          <Card title="Nombre de prévisions">
            <div style={styles.kpiValue}>{data?.forecasts_count ?? 0}</div>
          </Card>
          <Card title="Tickers suivis">
            <div style={styles.kpiValue}>{data?.tickers ?? 0}</div>
          </Card>
          <Card title="Horizons">
            <div style={styles.kpiValue}>
              {(data?.horizons || []).join(', ') || '—'}
            </div>
          </Card>
        </div>

        {/* Signaux et Risques - Using mock data for now */}
        {isLoading && <LoadingSpinner />}
        {error && <ErrorMessage message={String(error)} />}
        
        {!isLoading && !error && (
          <div style={styles.signalsGrid}>
            <TopSignals signals={[]} title="Top 3 Signaux (Données à venir)" />
            <TopRisks risks={[]} title="Top 3 Risques (Données à venir)" />
          </div>
        )}
      </div>
    </MainLayout>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 24,
  },
  pageTitle: {
    margin: 0,
    fontSize: 28,
    fontWeight: 700,
    color: '#fff',
  },
  filtersContainer: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 16,
  },
  filterGroup: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 8,
  },
  filterLabel: {
    fontWeight: 600,
    color: '#ccc',
    marginBottom: 4,
  },
  checkboxGroup: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    gap: 12,
    marginBottom: 8,
  },
  checkboxLabel: {
    display: 'flex' as const,
    alignItems: 'center' as const,
    gap: 4,
    fontSize: 14,
    cursor: 'pointer',
  },
  checkbox: {
    cursor: 'pointer',
  },
  textInput: {
    padding: '8px 12px',
    backgroundColor: '#222',
    border: '1px solid #444',
    borderRadius: 4,
    color: '#fff',
    fontSize: 14,
  },
  activeFilters: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    gap: 8,
    alignItems: 'center',
    padding: 8,
    backgroundColor: '#1a1a1a',
    borderRadius: 4,
    fontSize: 12,
  },
  filterBadge: {
    padding: '2px 8px',
    backgroundColor: '#4caf50',
    borderRadius: 12,
    color: '#000',
    fontWeight: 600,
    fontSize: 11,
  },
  kpisGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: 16,
  },
  kpiValue: {
    fontSize: 24,
    fontWeight: 600,
    color: '#4caf50',
  },
  signalsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
    gap: 24,
  },
}
