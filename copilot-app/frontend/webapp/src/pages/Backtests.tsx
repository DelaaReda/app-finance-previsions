// Page Backtests - Mini backtesting analysis
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/api/client'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import FreshnessBadge from '@/components/ui/FreshnessBadge'
import DataTable from '@/components/DataTable'
import { GridColDef } from '@mui/x-data-grid';

interface BacktestResult {
  results: {
    ok: boolean
    count_days: number
    avg_basket_return: number
    median: number
    stdev: number
    error?: string
  }
  params: {
    horizon: string
    top_n: number
    days_back: number
  }
  generated_at: string
  warning?: string
  detailed_results?: any[] // Added to represent possible detailed backtest results
}

export default function Backtests() {
  const [horizon, setHorizon] = useState<'1w' | '1m' | '1y'>('1m')
  const [topN, setTopN] = useState(5)
  const [daysBack, setDaysBack] = useState(180)

  const { data, isLoading, error } = useQuery({
    queryKey: ['backtests', horizon, topN, daysBack],
    queryFn: () => 
      apiGet<BacktestResult>('/backtests', { 
        horizon, 
        'top_n': String(topN), 
        'days_back': String(daysBack) 
      }).then(r => r.ok ? r.data : Promise.reject(r.error)),
    staleTime: 300000, // 5 minutes
  })

  // Define columns for the detailed results table (if available)
  const backtestColumns: GridColDef[] = [
    {
      field: 'period',
      headerName: 'Période',
      width: 150,
      type: 'string',
    },
    {
      field: 'return',
      headerName: 'Retour',
      width: 120,
      type: 'number',
      valueFormatter: (params) => params.value ? `${(params.value * 100).toFixed(2)}%` : '-',
    },
    {
      field: 'sharpe',
      headerName: 'Sharpe',
      width: 100,
      type: 'number',
      valueFormatter: (params) => params.value ? (params.value).toFixed(3) : '-',
    },
    {
      field: 'max_dd',
      headerName: 'Max DD',
      width: 120,
      type: 'string',
      valueFormatter: (params) => params.value ? (params.value).toFixed(2) : '-',
    },
  ];

  return (
    <MainLayout>
      <div style={styles.container}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={styles.pageTitle}>📊 Backtests - Analyse de Performance</h2>
          <FreshnessBadge 
            freshness={data?.generated_at ?? undefined} 
            stale={data?.generated_at ? new Date().getTime() - new Date(data.generated_at).getTime() > 3600000 : false} 
          />
        </div>

        {/* Configuration Panel */}
        <Card title="Configuration du Backtest">
          <div style={styles.configGrid}>
            <div>
              <label style={styles.label}>Horizon</label>
              <select 
                value={horizon} 
                onChange={(e) => setHorizon(e.target.value as '1w' | '1m' | '1y')}
                style={styles.select}
              >
                <option value="1w">1 Semaine</option>
                <option value="1m">1 Mois</option>
                <option value="1y">1 An</option>
              </select>
            </div>
            
            <div>
              <label style={styles.label}>Top-N</label>
              <input
                type="number"
                min="1"
                max="20"
                value={topN}
                onChange={(e) => setTopN(Math.max(1, Math.min(20, parseInt(e.target.value) || 5)))}
                style={styles.input}
              />
            </div>
            
            <div>
              <label style={styles.label}>Jours Historiques</label>
              <input
                type="number"
                min="30"
                max="365"
                value={daysBack}
                onChange={(e) => setDaysBack(Math.max(30, Math.min(365, parseInt(e.target.value) || 180)))}
                style={styles.input}
              />
            </div>
          </div>
        </Card>

        {/* Results */}
        {isLoading && <LoadingSpinner />}
        {error && <ErrorMessage message={String(error)} />}
        
        {data && data.results && (
          <Card title="Résultats du Backtest">
            <div style={styles.resultsGrid}>
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Jours de données</div>
                <div style={styles.metricValue}>{data?.results?.count_days ?? 0}</div>
              </div>
              
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Retour moyen</div>
                <div style={styles.metricValue}>
                  {data?.results?.avg_basket_return ? (data?.results?.avg_basket_return * 100).toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
              
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Écart-type</div>
                <div style={styles.metricValue}>
                  {data?.results?.stdev ? (data?.results?.stdev * 100).toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
              
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Médiane</div>
                <div style={styles.metricValue}>
                  {data?.results?.median ? (data?.results?.median * 100).toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
            </div>
            
            <div style={styles.detailsSection}>
              <h4>Paramètres de l'analyse</h4>
              <p>Horizon: {data?.params?.horizon || 'N/A'}</p>
              <p>Top-{data?.params?.top_n || 'N/A'} basket</p>
              <p>{data?.params?.days_back || 'N/A'} jours d'historique</p>
              <p>Généré le: {data?.generated_at ? new Date(data.generated_at).toLocaleString('fr-FR') : 'N/A'}</p>
              
              {data?.warning && (
                <div style={styles.warning}>
                  <strong>Avertissement:</strong> {data?.warning}
                </div>
              )}
            </div>
            
            {/* Add a detailed table if available */}
            {data?.detailed_results && data.detailed_results.length > 0 && (
              <div style={{ marginTop: 24 }}>
                <DataTable 
                  title="Résultats détaillés des backtests" 
                  columns={backtestColumns} 
                  rows={data.detailed_results} 
                  toolbar={true}
                  defaultPageSize={10}
                  pageSizeOptions={[5, 10, 25]}
                />
              </div>
            )}
          </Card>
        )}
      </div>
    </MainLayout>
  )
}

const styles = {
  container: { display: 'flex', flexDirection: 'column' as const, gap: 24 },
  pageTitle: { margin: 0, fontSize: 28, fontWeight: 700, color: '#fff' },
  configGrid: { 
    display: 'grid' as const, 
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
    gap: 16 
  },
  label: { display: 'block', marginBottom: 4, fontSize: 14, color: '#ccc' },
  select: { 
    width: '100%', 
    padding: '8px 12px', 
    backgroundColor: '#222', 
    border: '1px solid #444', 
    borderRadius: 4,
    color: '#fff',
    fontSize: 14,
  },
  input: { 
    width: '100%', 
    padding: '8px 12px', 
    backgroundColor: '#222', 
    border: '1px solid #444', 
    borderRadius: 4,
    color: '#fff',
    fontSize: 14,
  },
  resultsGrid: { 
    display: 'grid' as const, 
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
    gap: 16,
    marginBottom: 24
  },
  metricCard: { 
    padding: 16, 
    backgroundColor: '#1a1a1a', 
    borderRadius: 8, 
    textAlign: 'center' as const 
  },
  metricLabel: { fontSize: 12, color: '#999', marginBottom: 8 },
  metricValue: { fontSize: 20, fontWeight: 600, color: '#4caf50' },
  detailsSection: { 
    padding: 16, 
    backgroundColor: '#1a1a1a', 
    borderRadius: 8,
    fontSize: 14
  },
  warning: { 
    marginTop: 12, 
    padding: 12, 
    backgroundColor: '#3a2a15', 
    border: '1px solid #664', 
    borderRadius: 4,
    color: '#ff8800'
  }
}