// Composant pour afficher les Top 3 Signaux

import Card from '@/components/common/Card'
import { CompositeSignal } from '@/types/common.types'
import { safeGetArray, hasSafeArray, safeMap, safeLength } from '@/utils/safeAccess'

type TopSignalsProps = {
  signals: CompositeSignal[]
  title?: string
  emptyMessage?: string
}

const formatScore = (value?: number) =>
  value === undefined || value === null ? '—' : value.toFixed(0)

const getCompositeScore = (signal: CompositeSignal) =>
  signal.composite_score ?? signal.final_score ?? signal.score

const getComponentScores = (signal: CompositeSignal) => {
  const macro = signal.components?.macro?.macro_score ?? signal.macro_score
  const technical = signal.components?.technical?.technical_score ?? signal.technical_score
  const news = signal.components?.news?.news_score ?? signal.news_score

  return [
    { key: 'macro', label: 'Macro', score: macro },
    { key: 'technical', label: 'Technique', score: technical },
    { key: 'news', label: 'News', score: news }
  ].filter((item): item is { key: string; label: string; score: number } =>
    item.score !== undefined && item.score !== null
  )
}

const buildStrengthSummary = (signal: CompositeSignal) => {
  const components = getComponentScores(signal)
  if (safeLength(components) === 0) return undefined
  const strongest = components.reduce((best, current) =>
    current.score > best.score ? current : best
  )
  return `Forces dominantes: ${strongest.label} (${formatScore(strongest.score)}/100)`
}

const formatTimestamp = (timestamp?: string) => {
  if (!timestamp) return undefined
  const dt = new Date(timestamp)
  if (Number.isNaN(dt.getTime())) return undefined
  return dt.toLocaleString('fr-FR')
}

export default function TopSignals({
  signals,
  title = 'Top 3 Signaux',
  emptyMessage = 'Aucun signal disponible pour le moment.'
}: TopSignalsProps) {
  const topSignals = signals.filter(Boolean).slice(0, 3)

  return (
    <Card title={title}>
      <div style={styles.container}>
        {safeLength(topSignals) === 0 ? (
          <div style={styles.empty}>{emptyMessage}</div>
        ) : (
          safeMap(topSignals, (signal, index) => {
            const compositeScore = getCompositeScore(signal)
            const components = getComponentScores(signal)
            const strengthSummary = buildStrengthSummary(signal)
            const generatedAt = formatTimestamp(signal.timestamp)
            const description = signal.reason || signal.description || strengthSummary || 'Analyse détaillée non disponible.'

            return (
              <div key={`${signal.ticker}-${index}`} style={styles.signalCard}>
                <div style={styles.header}>
                  <span style={styles.rank}>#{index + 1}</span>
                  <span style={styles.ticker}>{signal.ticker}</span>
                  {compositeScore !== undefined && (
                    <span style={styles.scoreBadge}>{formatScore(compositeScore)}/100</span>
                  )}
                </div>

                <p style={styles.description}>{description}</p>

                <div style={styles.metrics}>
                  {safeMap(components, component => (
                    <span key={component.key} style={styles.metric}>
                      {component.label}: <strong>{formatScore(component.score)}</strong>
                    </span>
                  ))}
                </div>

                {(strengthSummary || generatedAt) && (
                  <div style={styles.footerRow}>
                    {strengthSummary && <span style={styles.subtle}>{strengthSummary}</span>}
                    {generatedAt && <span style={styles.timestamp}>Maj: {generatedAt}</span>}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </Card>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 16
  },
  empty: {
    padding: '16px 12px',
    borderRadius: 6,
    backgroundColor: '#1c1c1c',
    border: '1px dashed #333',
    color: '#888',
    fontSize: 13,
    textAlign: 'center' as const
  },
  signalCard: {
    backgroundColor: '#1d262f',
    borderRadius: 8,
    padding: 16,
    border: '1px solid #25394b',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 12
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12
  },
  rank: {
    backgroundColor: '#24313d',
    borderRadius: 6,
    padding: '4px 10px',
    fontSize: 12,
    fontWeight: 600,
    color: '#8bc4ff'
  },
  ticker: {
    fontSize: 16,
    fontWeight: 600,
    letterSpacing: 0.5
  },
  scoreBadge: {
    marginLeft: 'auto',
    backgroundColor: '#1f3a2b',
    color: '#6be592',
    padding: '4px 10px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 600
  },
  description: {
    margin: 0,
    fontSize: 13,
    color: '#cfd8dc',
    lineHeight: 1.5
  },
  metrics: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 8
  },
  metric: {
    backgroundColor: '#25394b',
    borderRadius: 999,
    padding: '4px 10px',
    fontSize: 12,
    color: '#b0bec5'
  },
  footerRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 8,
    alignItems: 'center'
  },
  subtle: {
    fontSize: 12,
    color: '#90a4ae'
  },
  timestamp: {
    fontSize: 11,
    color: '#607d8b',
    marginLeft: 'auto'
  }
}
