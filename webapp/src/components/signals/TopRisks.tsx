// Composant pour afficher les Top 3 Risques

import { Signal } from '@/types/common.types'
import Card from '@/components/common/Card'

type TopRisksProps = {
  risks: Signal[]
  title?: string
}

export default function TopRisks({ risks, title = 'Top 3 Risques' }: TopRisksProps) {
  const topRisks = risks.slice(0, 3)

  return (
    <Card title={title}>
      <div style={styles.container}>
        {topRisks.map((risk, index) => (
          <div key={risk.id} style={styles.riskCard}>
            <div style={styles.header}>
              <span style={styles.rank}>#{index + 1}</span>
              <span style={styles.icon}>⚠️</span>
              <span style={styles.severity}>
                {risk.score > 70 ? 'Élevé' : risk.score > 40 ? 'Moyen' : 'Faible'}
              </span>
            </div>
            <h4 style={styles.title}>{risk.title}</h4>
            <p style={styles.description}>{risk.description}</p>
            <div style={styles.footer}>
              <span style={styles.horizon}>{risk.horizon}</span>
              <span style={styles.score}>{risk.score.toFixed(0)}/100</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 16,
  },
  riskCard: {
    backgroundColor: '#2a1515',
    borderRadius: 6,
    padding: 16,
    border: '1px solid #4a2020',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  rank: {
    backgroundColor: '#4a2020',
    borderRadius: 4,
    padding: '2px 8px',
    fontSize: 12,
    fontWeight: 600,
    color: '#ff6b6b',
  },
  icon: {
    fontSize: 18,
  },
  severity: {
    fontSize: 12,
    fontWeight: 600,
    color: '#ff6b6b',
  },
  title: {
    margin: 0,
    fontSize: 15,
    fontWeight: 600,
    marginBottom: 6,
    color: '#fff',
  },
  description: {
    margin: 0,
    fontSize: 13,
    color: '#ccc',
    lineHeight: 1.5,
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 12,
    borderTop: '1px solid #4a2020',
  },
  horizon: {
    fontSize: 12,
    padding: '2px 8px',
    backgroundColor: '#3a2a1a',
    borderRadius: 4,
    color: '#ffb74d',
  },
  score: {
    fontSize: 13,
    fontWeight: 600,
    color: '#ff6b6b',
  },
}
