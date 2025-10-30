// Page Macro - Pilier 1: FRED, VIX, GSCPI, GPR

import { useQuery } from '@tanstack/react-query'
import { macroService } from '@/services/macro.service'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function Macro() {
  const { data: dashboard, isLoading, error } = useQuery({
    queryKey: ['macro-dashboard'],
    queryFn: async () => {
      const result = await macroService.getDashboard()
      if (!result.ok) throw new Error(result.error)
      return result.data
    },
    staleTime: 30_000,
  })

  if (isLoading) return <MainLayout><LoadingSpinner /></MainLayout>
  if (error) return <MainLayout><ErrorMessage message={String(error)} /></MainLayout>

  return (
    <MainLayout>
      <div style={styles.container}>
        <h2 style={styles.pageTitle}>📊 Macro - Indicateurs Économiques</h2>
        
        {/* Régime actuel */}
        {dashboard?.regime && (
          <Card title="Régime Macro Actuel">
            <div style={styles.regimeContainer}>
              <div style={styles.regimeValue}>{dashboard.regime.current}</div>
              <div style={styles.confidence}>
                Confiance: {(dashboard.regime.confidence * 100).toFixed(0)}%
              </div>
              <div style={styles.changeDate}>
                Depuis: {new Date(dashboard.regime.changeDate).toLocaleDateString('fr-FR')}
              </div>
            </div>
          </Card>
        )}

        {/* Indicateurs par catégorie */}
        <div style={styles.indicatorsGrid}>
          {dashboard?.indicators && dashboard.indicators.map((indicator) => (
            <Card key={indicator.id} title={indicator.name}>
              <div style={styles.indicatorContent}>
                <div style={styles.indicatorValue}>
                  {indicator.value.toFixed(2)} {indicator.unit || ''}
                </div>
                <div style={indicator.change >= 0 ? styles.changePositive : styles.changeNegative}>
                  {indicator.change >= 0 ? '↗' : '↘'} {Math.abs(indicator.changePercent).toFixed(2)}%
                </div>
                <div style={styles.category}>{indicator.category}</div>
                <div style={styles.timestamp}>
                  MAJ: {new Date(indicator.timestamp).toLocaleDateString('fr-FR')}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Alertes */}
        {dashboard?.alerts && dashboard.alerts.length > 0 && (
          <Card title="Alertes Macro">
            <div style={styles.alertsList}>
              {dashboard.alerts.map((alert, index) => (
                <div key={index} style={getSeverityStyle(alert.severity)}>
                  <div style={styles.alertHeader}>
                    <span style={styles.alertType}>{alert.type}</span>
                    <span style={styles.alertSeverity}>{alert.severity}</span>
                  </div>
                  <div style={styles.alertMessage}>{alert.message}</div>
                  <div style={styles.alertTime}>
                    {new Date(alert.timestamp).toLocaleString('fr-FR')}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </MainLayout>
  )
}

function getSeverityStyle(severity: 'low' | 'medium' | 'high') {
  const baseStyle = {
    padding: 12,
    borderRadius: 6,
    marginBottom: 8,
    border: '1px solid',
  }
  
  const colors = {
    low: { bg: '#1a2a1a', border: '#2a4a2a', color: '#4caf50' },
    medium: { bg: '#2a2a1a', border: '#4a4a2a', color: '#ffb74d' },
    high: { bg: '#2a1515', border: '#4a2020', color: '#f44336' },
  }
  
  return {
    ...baseStyle,
    backgroundColor: colors[severity].bg,
    borderColor: colors[severity].border,
    color: colors[severity].color,
  }
}

const styles = {
  container: { display: 'flex', flexDirection: 'column' as const, gap: 24 },
  pageTitle: { margin: 0, fontSize: 28, fontWeight: 700, color: '#fff' },
  regimeContainer: { display: 'flex', flexDirection: 'column' as const, gap: 8 },
  regimeValue: { fontSize: 32, fontWeight: 700, color: '#4caf50' },
  confidence: { fontSize: 14, color: '#999' },
  changeDate: { fontSize: 13, color: '#666' },
  indicatorsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 16,
  },
  indicatorContent: { display: 'flex', flexDirection: 'column' as const, gap: 8 },
  indicatorValue: { fontSize: 28, fontWeight: 700, color: '#fff' },
  changePositive: { fontSize: 16, color: '#4caf50', fontWeight: 600 },
  changeNegative: { fontSize: 16, color: '#f44336', fontWeight: 600 },
  category: { fontSize: 12, color: '#999', textTransform: 'uppercase' as const },
  timestamp: { fontSize: 11, color: '#666' },
  alertsList: { display: 'flex', flexDirection: 'column' as const },
  alertHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: 4 },
  alertType: { fontSize: 12, fontWeight: 600, textTransform: 'uppercase' as const },
  alertSeverity: { fontSize: 12, fontWeight: 600 },
  alertMessage: { fontSize: 14, marginBottom: 4 },
  alertTime: { fontSize: 11, opacity: 0.7 },
}
