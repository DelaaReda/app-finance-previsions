// Dashboard principal - Vue d'ensemble avec Top 3 Signaux/Risques

import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/services/api'
import { Signal } from '@/types/common.types'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import TopSignals from '@/components/signals/TopSignals'
import TopRisks from '@/components/signals/TopRisks'

type DashboardData = {
  kpis: {
    last_forecast_dt?: string | null
    forecasts_count?: number
    tickers?: number
    horizons?: string[]
    last_macro_dt?: string | null
    last_quality_dt?: string | null
  }
  top_signals: Signal[]
  top_risks: Signal[]
  market_overview: {
    sp500_change: number
    vix_level: number
    market_sentiment: 'bullish' | 'bearish' | 'neutral'
  }
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiGet<DashboardData>('/dashboard').then(r => 
      r.ok ? r.data : Promise.reject(r.error)
    ),
    staleTime: 15_000,
  })

  if (isLoading) return <MainLayout><LoadingSpinner /></MainLayout>
  if (error) return <MainLayout><ErrorMessage message={String(error)} /></MainLayout>
  if (!data) return <MainLayout><ErrorMessage message="Aucune donnée disponible" /></MainLayout>

  return (
    <MainLayout>
      <div style={styles.container}>
        <h2 style={styles.pageTitle}>Dashboard - Vue d'ensemble</h2>
        
        {/* KPIs Grid */}
        <div style={styles.kpisGrid}>
          <Card title="Dernière prévision">
            <div style={styles.kpiValue}>{data.kpis.last_forecast_dt || '—'}</div>
          </Card>
          <Card title="Nombre de prévisions">
            <div style={styles.kpiValue}>{data.kpis.forecasts_count ?? 0}</div>
          </Card>
          <Card title="Tickers suivis">
            <div style={styles.kpiValue}>{data.kpis.tickers ?? 0}</div>
          </Card>
          <Card title="Horizons">
            <div style={styles.kpiValue}>
              {(data.kpis.horizons || []).join(', ') || '—'}
            </div>
          </Card>
        </div>

        {/* Signaux et Risques */}
        <div style={styles.signalsGrid}>
          <TopSignals signals={data.top_signals || []} />
          <TopRisks risks={data.top_risks || []} />
        </div>
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
  kpisGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
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
