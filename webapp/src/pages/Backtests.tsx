// Page Backtests - Mini backtesting analysis
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/api/client'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

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

  return (
    <MainLayout>
      <div style={styles.container}>
        <h2 style={styles.pageTitle}>📊 Backtests - Analyse de Performance</h2>

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
        
        {data && (
          <Card title="Résultats du Backtest">
            <div style={styles.resultsGrid}>
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Jours de données</div>
                <div style={styles.metricValue}>{data.results.count_days}</div>
              </div>
              
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Retour moyen</div>
                <div style={styles.metricValue}>
                  {data.results.avg_basket_return ? (data.results.avg_basket_return * 100).toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
              
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Écart-type</div>
                <div style={styles.metricValue}>
                  {data.results.stdev ? (data.results.stdev * 100).toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
              
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Médiane</div>
                <div style={styles.metricValue}>
                  {data.results.median ? (data.results.median * 100).toFixed(2) + '%' : 'N/A'}
                </div>
              </div>
            </div>
            
            <div style={styles.detailsSection}>
              <h4>Paramètres de l'analyse</h4>
              <p>Horizon: {data.params.horizon}</p>
              <p>Top-{data.params.top_n} basket</p>
              <p>{data.params.days_back} jours d'historique</p>
              <p>Généré le: {new Date(data.generated_at).toLocaleString('fr-FR')}</p>
              
              {data.warning && (
                <div style={styles.warning}>
                  <strong>Avertissement:</strong> {data.warning}
                </div>
              )}
            </div>
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