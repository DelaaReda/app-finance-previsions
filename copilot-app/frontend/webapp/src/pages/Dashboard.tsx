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
import { safeGetArray, hasSafeArray, safeMap, safeLength } from '@/utils/safeAccess'
import type { CompositeSignal } from '@/types/common.types'

type DashboardData = {
  last_forecast_dt?: string | null
  forecasts_count?: number
  tickers?: number
  horizons?: string[]
  last_macro_dt?: string | null
  last_quality_dt?: string | null
  filtered_signals?: CompositeSignal[]
  filtered_risks?: CompositeSignal[]
  filtered_ticker_count?: number
  generated_at?: string
  filter_applied?: {
    sectors: string[]
    horizons: string[]
    themes: string[]
    tickers: string[]
  }
  error?: string
}

export default function Dashboard() {
  const [sectors, setSectors] = useState<string[]>([])
  const [horizons, setHorizons] = useState<string[]>([])
  const [themes, setThemes] = useState<string[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  const [includeSignals, setIncludeSignals] = useState<boolean>(false)  // Heavy mode toggle

  // Sector options
  const sectorOptions = ["Technology", "Healthcare", "Financials", "Consumer", "Industrials", "Energy", "Utilities", "Real Estate"]
  // Horizon options
  const horizonOptions = ["short", "medium", "long"]
  // Theme options
  const themeOptions = ["growth", "value", "momentum", "dividend", "quality"]

  const { data, isLoading, error, isFetching } = useQuery<DashboardData>({
    queryKey: ['dashboard', { sectors, horizons, themes, tickers, includeSignals }],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (safeLength(sectors) > 0) params.sectors = sectors.join(',')
      if (safeLength(horizons) > 0) params.horizons = horizons.join(',')
      if (safeLength(themes) > 0) params.themes = themes.join(',')
      if (safeLength(tickers) > 0) params.tickers = tickers.join(',')
      if (includeSignals) params.include_signals = '1'  // Add heavy mode flag

      const response = await apiGet<DashboardData>('/dashboard/kpis', params)
      if (!response.ok) {
        throw new Error(response.error || 'Échec du chargement du dashboard')
      }
      return response.data
    },
    staleTime: 15_000,
  })

  const signals = data?.filtered_signals ?? []
  const risks = data?.filtered_risks ?? []
  const generatedAt = data?.generated_at ? new Date(data.generated_at) : undefined
  const filtersApplied = data?.filter_applied

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
    setTickers(value ? safeMap(value.split(','), t => t.trim().toUpperCase()) : [])
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
                {safeMap(sectorOptions, sector => (
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
                {safeMap(horizonOptions, horizon => (
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
                {safeMap(themeOptions, theme => (
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

            {/* Toggle for heavy processing mode */}
            <div style={styles.filterGroup}>
              <label style={styles.filterLabel}>
                Mode détaillé: 
                <input
                  type="checkbox"
                  checked={includeSignals}
                  onChange={(e) => setIncludeSignals(e.target.checked)}
                  disabled={isFetching}  // Disable during fetch to prevent multiple parallel requests
                  style={styles.toggleSwitch}
                />
                <span style={styles.toggleLabel}>{includeSignals ? ' Activé' : ' Désactivé'}</span>
              </label>
            </div>

          {(safeLength(sectors) > 0 || safeLength(horizons) > 0 || safeLength(themes) > 0 || safeLength(tickers) > 0 || includeSignals) && (
            <div style={styles.activeFilters}>
              <small>Filtres actifs:</small>
              {safeLength(sectors) > 0 && <span style={styles.filterBadge}>Secteurs: {sectors.join(', ')}</span>}
              {safeLength(horizons) > 0 && <span style={styles.filterBadge}>Horizons: {horizons.join(', ')}</span>}
              {safeLength(themes) > 0 && <span style={styles.filterBadge}>Thèmes: {themes.join(', ')}</span>}
              {safeLength(tickers) > 0 && <span style={styles.filterBadge}>Tickers: {tickers.join(', ')}</span>}
              {includeSignals && <span style={styles.filterBadge}>Mode détaillé: ON</span>}
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

        {(isLoading || isFetching) && <LoadingSpinner />}
        {error && <ErrorMessage message={String(error)} />}
        {!error && data?.error && <ErrorMessage message={data.error} />}

        {!isLoading && !error && (
          <>
            <div style={styles.metaRow}>
              <span style={styles.metaLabel}>
                Univers analysé: <strong>{data?.filtered_ticker_count ?? data?.tickers ?? 0}</strong> tickers
              </span>
              {filtersApplied && (
                <span style={styles.metaLabel}>
                  Filtres appliqués côté API: {[
                    filtersApplied.sectors && safeLength(filtersApplied.sectors) > 0 ? `Secteurs (${filtersApplied.sectors.length})` : null,
                    filtersApplied.horizons && safeLength(filtersApplied.horizons) > 0 ? `Horizons (${filtersApplied.horizons.join(', ')})` : null,
                    filtersApplied.themes && safeLength(filtersApplied.themes) > 0 ? `Thèmes (${filtersApplied.themes.join(', ')})` : null,
                    filtersApplied.tickers && safeLength(filtersApplied.tickers) > 0 ? `Tickers (${filtersApplied.tickers.join(', ')})` : null,
                  ].filter(Boolean).join(' • ') || 'Aucun'}
                </span>
              )}
              {generatedAt && (
                <span style={styles.metaLabel}>
                  Mise à jour: {generatedAt.toLocaleString('fr-FR')}
                </span>
              )}
            </div>

            <div style={styles.signalsGrid}>
              <TopSignals
                signals={signals}
                title="Top 3 Signaux"
                emptyMessage="Aucun signal détecté pour les filtres sélectionnés."
              />
              <TopRisks
                risks={risks}
                title="Top 3 Risques"
                emptyMessage="Aucun risque majeur détecté pour les filtres sélectionnés."
              />
            </div>
          </>
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
  toggleSwitch: {
    marginLeft: 8,
    transform: 'scale(1.2)',
    cursor: 'pointer',
  },
  toggleLabel: {
    marginLeft: 4,
    fontSize: 14,
    color: '#4caf50',
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
  metaRow: {
    display: 'flex' as const,
    flexDirection: 'column' as const,
    gap: 6,
    padding: '12px 16px',
    backgroundColor: '#1a1a1a',
    borderRadius: 6,
    border: '1px solid #2a2a2a',
    fontSize: 12,
    color: '#bbb',
  },
  metaLabel: {
    display: 'block',
  },
  signalsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
    gap: 24,
  },
}
