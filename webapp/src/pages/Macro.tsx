/**
 * Page Macro - Pilier 1
 * FRED, VIX, GSCPI, GPR, inflation, emploi, liquidité
 */

import { useMacroDashboard } from '@/hooks/useMacroData'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function Macro() {
  const { data, isLoading, error } = useMacroDashboard()

  if (isLoading) return <LoadingSpinner message="Chargement des données macro..." />
  if (error) return <ErrorMessage error={error as Error} />
  if (!data) return <div>Aucune donnée disponible</div>

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>📊 Macro Dashboard</h1>
      
      <div style={{
        display: 'grid',
        gap: '1.5rem',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        marginBottom: '2rem',
      }}>
        <IndicatorCard indicator={data.vix} />
        <IndicatorCard indicator={data.gscpi} />
        <IndicatorCard indicator={data.gpr} />
        <IndicatorCard indicator={data.fed_funds_rate} />
        <IndicatorCard indicator={data.unemployment} />
        <IndicatorCard indicator={data.cpi} />
      </div>

      {data.custom_indicators && data.custom_indicators.length > 0 && (
        <div>
          <h2 style={{ marginBottom: '1rem' }}>Indicateurs personnalisés</h2>
          <div style={{
            display: 'grid',
            gap: '1.5rem',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          }}>
            {data.custom_indicators.map((indicator) => (
              <IndicatorCard key={indicator.id} indicator={indicator} />
            ))}
          </div>
        </div>
      )}

      <div style={{ marginTop: '1rem', fontSize: '0.85rem', color: '#666' }}>
        Dernière mise à jour: {data.last_updated}
      </div>
    </div>
  )
}
import type { MacroIndicator } from '@/types'

function IndicatorCard({ indicator }: { indicator: MacroIndicator }) {
  const trendColor = indicator.trend === 'up' ? '#4ade80' : indicator.trend === 'down' ? '#f87171' : '#94a3b8'
  const alertColor = indicator.alert_level === 'critical' ? '#ef4444' : indicator.alert_level === 'warning' ? '#f59e0b' : '#6b7280'
  
  return (
    <Card
      title={indicator.name}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{indicator.source.name}</span>
          <span>{new Date(indicator.timestamp).toLocaleDateString()}</span>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
          {indicator.current_value.toFixed(2)}
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: trendColor, fontWeight: 600 }}>
            {indicator.trend === 'up' ? '↑' : indicator.trend === 'down' ? '↓' : '→'}
            {' '}
            {Math.abs(indicator.change_pct).toFixed(2)}%
          </span>
          <span style={{ color: '#888', fontSize: '0.9rem' }}>
            vs {indicator.previous_value.toFixed(2)}
          </span>
        </div>

        {indicator.alert_level && indicator.alert_level !== 'normal' && (
          <div style={{
            padding: '0.5rem',
            backgroundColor: alertColor + '22',
            border: `1px solid ${alertColor}`,
            borderRadius: '4px',
            fontSize: '0.85rem',
            color: alertColor,
          }}>
            ⚠️ {indicator.alert_level === 'critical' ? 'Critique' : 'Attention'}
          </div>
        )}
      </div>
    </Card>
  )
}
