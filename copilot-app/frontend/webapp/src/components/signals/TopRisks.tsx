// Composant pour afficher les Top 3 Risques

import Card from '@/components/common/Card'
import { CompositeSignal } from '@/types/common.types'
import { safeMap, safeLength } from '@/lib/safe'
import { formatScore as formatScore100 } from '@/utils/score'

type TopRisksProps = {
  risks: CompositeSignal[]
  title?: string
  emptyMessage?: string
}

const getCompositeScore = (risk: CompositeSignal) =>
  risk.composite_score ?? risk.final_score ?? risk.score

const getComponentScores = (risk: CompositeSignal) => {
  const macro = risk.components?.macro?.macro_score ?? risk.macro_score
  const technical = risk.components?.technical?.technical_score ?? risk.technical_score
  const news = risk.components?.news?.news_score ?? risk.news_score

  return [
    { key: 'macro', label: 'Macro', score: macro },
    { key: 'technical', label: 'Technique', score: technical },
    { key: 'news', label: 'News', score: news }
  ].filter((item): item is { key: string; label: string; score: number } =>
    item.score !== undefined && item.score !== null
  )
}

const buildWeaknessSummary = (risk: CompositeSignal) => {
  const components = getComponentScores(risk)
  if (safeLength(components) === 0) return undefined
  const weakest = components.reduce((worst, current) =>
    current.score < worst.score ? current : worst
  )
  return `Faiblesse principale: ${weakest.label} (${formatScore100(weakest.score)})`
}

const getSeverity = (score?: number) => {
  if (score === undefined || score === null) return { label: 'Inconnu', tone: '#cfd8dc' }
  if (score < 30) return { label: 'Critique', tone: '#ff5252' }
  if (score < 45) return { label: 'Élevé', tone: '#ff7043' }
  if (score < 60) return { label: 'Modéré', tone: '#ffb74d' }
  return { label: 'Surveiller', tone: '#ffe082' }
}

const formatTimestamp = (timestamp?: string) => {
  if (!timestamp) return undefined
  const dt = new Date(timestamp)
  if (Number.isNaN(dt.getTime())) return undefined
  return dt.toLocaleString('fr-FR')
}

export default function TopRisks({
  risks,
  title = 'Top 3 Risques',
  emptyMessage = 'Aucun risque notable détecté pour le moment.'
}: TopRisksProps) {
  const topRisks = risks.filter(Boolean).slice(0, 3)

  return (
    <Card title={title}>
      <div style={styles.container}>
        {safeLength(topRisks) === 0 ? (
          <div style={styles.empty}>{emptyMessage}</div>
        ) : (
          safeMap<CompositeSignal, JSX.Element>(topRisks, (risk, index) => {
            const compositeScore = getCompositeScore(risk)
            const { label: severityLabel, tone: severityTone } = getSeverity(compositeScore)
            const components = getComponentScores(risk)
            const weaknessSummary = buildWeaknessSummary(risk)
            const generatedAt = formatTimestamp(risk.timestamp)
            const description = risk.reason || risk.description || weaknessSummary || 'Analyse détaillée non disponible.'

            return (
              <div key={`${risk.ticker}-${index}`} style={styles.riskCard}>
                <div style={styles.header}>
                  <span style={styles.rank}>#{index + 1}</span>
                  <span style={styles.icon} aria-hidden>⚠️</span>
                  <span style={{ ...styles.severity, color: severityTone }}>{severityLabel}</span>
                  {compositeScore !== undefined && (
                    <span style={styles.scoreBadge}>{formatScore100(compositeScore)}</span>
                  )}
                </div>

                <h4 style={styles.title}>{risk.ticker || risk.type || `Risque ${index + 1}`}</h4>
                <p style={styles.description}>{description}</p>

                <div style={styles.metrics}>
                  {safeMap<{ key: string; label: string; score: number }, JSX.Element>(components, component => (
                    <span key={component.key} style={styles.metric}>
                      {component.label}: <strong>{formatScore100(component.score)}</strong>
                    </span>
                  ))}
                </div>

                {(weaknessSummary || generatedAt) && (
                  <div style={styles.footerRow}>
                    {weaknessSummary && <span style={styles.subtle}>{weaknessSummary}</span>}
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
    backgroundColor: '#2a1a1a',
    border: '1px dashed #5c2a2a',
    color: '#ff9e80',
    fontSize: 13,
    textAlign: 'center' as const
  },
  riskCard: {
    backgroundColor: '#2b1d1d',
    borderRadius: 8,
    padding: 16,
    border: '1px solid #4a2b2b',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 12
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 10
  },
  rank: {
    backgroundColor: '#4a2020',
    borderRadius: 6,
    padding: '4px 10px',
    fontSize: 12,
    fontWeight: 600,
    color: '#ff8a80'
  },
  icon: {
    fontSize: 18
  },
  severity: {
    fontSize: 12,
    fontWeight: 600
  },
  scoreBadge: {
    marginLeft: 'auto',
    backgroundColor: '#452121',
    color: '#ffab91',
    padding: '4px 10px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 600
  },
  title: {
    margin: 0,
    fontSize: 16,
    fontWeight: 600,
    color: '#ffe0b2'
  },
  description: {
    margin: 0,
    fontSize: 13,
    color: '#ffccbc',
    lineHeight: 1.5
  },
  metrics: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 8
  },
  metric: {
    backgroundColor: '#452121',
    borderRadius: 999,
    padding: '4px 10px',
    fontSize: 12,
    color: '#ffcdd2'
  },
  footerRow: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 8,
    alignItems: 'center'
  },
  subtle: {
    fontSize: 12,
    color: '#ffab91'
  },
  timestamp: {
    fontSize: 11,
    color: '#ffccbc',
    marginLeft: 'auto'
  }
}
