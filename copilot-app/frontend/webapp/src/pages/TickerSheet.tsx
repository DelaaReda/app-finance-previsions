/**
 * Page TickerSheet
 * Fiche détaillée par ticker avec prix, technique, news
 */

import { useParams } from 'react-router-dom'
import { useStockAnalysis } from '@/hooks/useStockData'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import { safeGetArray, hasSafeArray, safeMap } from '@/lib/safe'

export default function TickerSheet() {
  const { ticker } = useParams<{ ticker: string }>()
  const { data, isLoading, error } = useStockAnalysis(ticker || '')

  // Backend may wrap payload in an ApiResponse-like envelope; normalize to raw payload
  const payload: any = (data as any)?.data ?? data;

  if (!ticker) {
    return <ErrorMessage message="Ticker manquant" />
  }

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={String(error)} />
  if (!payload) return <div>Aucune donnée disponible</div>

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>
  {payload.ticker} • {payload.name}
      </h1>

      <div style={{ display: 'grid', gap: '1.5rem' }}>
        {/* Prix et performance */}
        <Card title="Prix et Performance">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.85rem', color: '#888' }}>Prix actuel</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>${payload.current_price.toFixed(2)}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: '#888' }}>Variation</div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: 'bold',
                color: payload.change_pct >= 0 ? '#4ade80' : '#f87171',
              }}>
                {payload.change_pct >= 0 ? '+' : ''}{payload.change_pct.toFixed(2)}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.85rem', color: '#888' }}>Volume</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                {(payload.volume / 1000000).toFixed(2)}M
              </div>
            </div>
          </div>
        </Card>

        {/* Indicateurs techniques */}
        <Card title="Indicateurs Techniques">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
            {payload.technical?.sma_20 && (
              <TechIndicator label="SMA 20" value={payload.technical.sma_20.toFixed(2)} />
            )}
            {payload.technical?.sma_50 && (
              <TechIndicator label="SMA 50" value={payload.technical.sma_50.toFixed(2)} />
            )}
            {payload.technical?.rsi && (
              <TechIndicator 
                label="RSI" 
                value={payload.technical.rsi.toFixed(1)}
                color={payload.technical.rsi > 70 ? '#f87171' : payload.technical.rsi < 30 ? '#4ade80' : undefined}
              />
            )}
          </div>
        </Card>
        {/* Score composite */}
        <Card title="Score Composite (40/40/20)">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
            <ScoreBox label="Macro" value={payload.score?.macro ?? 0} />
            <ScoreBox label="Technique" value={payload.score?.technical ?? 0} />
            <ScoreBox label="News" value={payload.score?.news ?? 0} />
            <ScoreBox label="Composite" value={payload.score?.composite ?? 0} highlight />
          </div>
        </Card>

        {/* Alertes */}
  {hasSafeArray(payload, 'alerts') && (
          <Card title="🔔 Alertes">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {safeMap(safeGetArray(payload, 'alerts'), (alert: any, idx: number) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: alert.severity === 'critical' ? '#2a1a1a' : alert.severity === 'warning' ? '#2a2a1a' : '#1a2a2a',
                    border: `1px solid ${alert.severity === 'critical' ? '#ff4444' : alert.severity === 'warning' ? '#ffaa44' : '#4444ff'}`,
                    borderRadius: '6px',
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{alert.type}</div>
                  <div style={{ fontSize: '0.9rem', color: '#ccc' }}>{alert.message}</div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Sources */}
        <div style={{ fontSize: '0.85rem', color: '#666' }}>
          Dernière mise à jour: {payload.last_updated}
        </div>
      </div>
    </div>
  )
}

function TechIndicator({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: '0.8rem', color: '#888' }}>{label}</div>
      <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: color || '#fff' }}>{value}</div>
    </div>
  )
}

function ScoreBox({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div style={{
      padding: '0.75rem',
      backgroundColor: highlight ? '#1a2a3a' : '#1a1a1a',
      borderRadius: '6px',
      border: highlight ? '1px solid #4a9eff' : '1px solid #333',
    }}>
      <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '0.25rem' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: highlight ? '#4a9eff' : '#fff' }}>
        {value.toFixed(1)}
      </div>
    </div>
  )
}
