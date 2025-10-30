// Composant pour afficher les Top 3 Signaux

import { Signal } from '@/types/common.types'
import Card from '@/components/common/Card'

type TopSignalsProps = {
  signals: Signal[]
  title?: string
}

export default function TopSignals({ signals, title = 'Top 3 Signaux' }: TopSignalsProps) {
  const topSignals = signals.slice(0, 3)

  return (
    <Card title={title}>
      <div style={styles.container}>
        {topSignals.map((signal, index) => (
          <div key={signal.id} style={styles.signalCard}>
            <div style={styles.header}>
              <span style={styles.rank}>#{index + 1}</span>
              <span style={getTypeStyle(signal.type)}>
                {signal.type === 'bullish' ? '📈' : signal.type === 'bearish' ? '📉' : '➡️'}
              </span>
              <span style={styles.score}>{signal.score.toFixed(0)}/100</span>
            </div>
            <h4 style={styles.title}>{signal.title}</h4>
            <p style={styles.description}>{signal.description}</p>
            <div style={styles.footer}>
              <span style={styles.horizon}>{signal.horizon}</span>
              <span style={styles.sources}>{signal.sources.length} source(s)</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function getTypeStyle(type: Signal['type']) {
  const colors = {
    bullish: '#4caf50',
    bearish: '#f44336',
    neutral: '#999'
  }
  return { color: colors[type], fontSize: 20 }
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 16,
  },
  signalCard: {
    backgroundColor: '#222',
    borderRadius: 6,
    padding: 16,
    border: '1px solid #333',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  rank: {
    backgroundColor: '#333',
    borderRadius: 4,
    padding: '2px 8px',
    fontSize: 12,
    fontWeight: 600,
  },
  score: {
    marginLeft: 'auto',
    fontSize: 14,
    fontWeight: 600,
    color: '#4caf50',
  },
  title: {
    margin: 0,
    fontSize: 15,
    fontWeight: 600,
    marginBottom: 6,
  },
  description: {
    margin: 0,
    fontSize: 13,
    color: '#aaa',
    lineHeight: 1.5,
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTop: '1px solid #333',
  },
  horizon: {
    fontSize: 12,
    padding: '2px 8px',
    backgroundColor: '#1a3a52',
    borderRadius: 4,
    color: '#64b5f6',
  },
  sources: {
    fontSize: 11,
    color: '#666',
  },
}
