/**
 * Composant TopSignals
 * Affiche les Top 3 signaux (opportunités)
 * Basé sur VISION: Signal > Bruit
 */

import Card from '../common/Card'
import type { Signal } from '@/types'

type TopSignalsProps = {
  signals: Signal[]
  loading?: boolean
}

export default function TopSignals({ signals, loading }: TopSignalsProps) {
  if (loading) {
    return <Card title="🚀 Top 3 Signaux"><div style={{ color: '#888' }}>Chargement...</div></Card>
  }

  return (
    <Card title="🚀 Top 3 Signaux">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {signals.slice(0, 3).map((signal, idx) => (
          <SignalCard key={signal.id} signal={signal} rank={idx + 1} />
        ))}
        
        {signals.length === 0 && (
          <div style={{ color: '#888', textAlign: 'center', padding: '1rem' }}>
            Aucun signal disponible
          </div>
        )}
      </div>
    </Card>
  )
}
function SignalCard({ signal, rank }: { signal: Signal; rank: number }) {
  return (
    <div style={{
      backgroundColor: '#1a2a1a',
      border: '1px solid #2a4a2a',
      borderRadius: '6px',
      padding: '0.75rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <div style={{
          backgroundColor: '#2a5a2a',
          color: '#6fff6f',
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 'bold',
          fontSize: '0.85rem',
        }}>
          {rank}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, color: '#6fff6f' }}>{signal.title}</div>
          <div style={{ fontSize: '0.8rem', color: '#888' }}>
            {signal.category} • {signal.horizon} • Score: {signal.score.toFixed(1)}
          </div>
        </div>
      </div>
      <div style={{ fontSize: '0.9rem', color: '#ccc', marginBottom: '0.5rem' }}>
        {signal.description}
      </div>
    </div>
  )
}
