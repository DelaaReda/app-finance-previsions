/**
 * Composant TopRisks
 * Affiche les Top 3 risques
 * Basé sur VISION: Signal > Bruit
 */

import Card from '../common/Card'
import type { Signal } from '@/types'

type TopRisksProps = {
  risks: Signal[]
  loading?: boolean
}

export default function TopRisks({ risks, loading }: TopRisksProps) {
  if (loading) {
    return <Card title="⚠️ Top 3 Risques"><div style={{ color: '#888' }}>Chargement...</div></Card>
  }

  return (
    <Card title="⚠️ Top 3 Risques">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {risks.slice(0, 3).map((risk, idx) => (
          <RiskCard key={risk.id} risk={risk} rank={idx + 1} />
        ))}
        
        {risks.length === 0 && (
          <div style={{ color: '#888', textAlign: 'center', padding: '1rem' }}>
            Aucun risque identifié
          </div>
        )}
      </div>
    </Card>
  )
}
function RiskCard({ risk, rank }: { risk: Signal; rank: number }) {
  return (
    <div style={{
      backgroundColor: '#2a1a1a',
      border: '1px solid #4a2a2a',
      borderRadius: '6px',
      padding: '0.75rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
        <div style={{
          backgroundColor: '#5a2a2a',
          color: '#ff6f6f',
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
          <div style={{ fontWeight: 600, color: '#ff6f6f' }}>{risk.title}</div>
          <div style={{ fontSize: '0.8rem', color: '#888' }}>
            {risk.category} • {risk.horizon} • Score: {risk.score.toFixed(1)}
          </div>
        </div>
      </div>
      <div style={{ fontSize: '0.9rem', color: '#ccc', marginBottom: '0.5rem' }}>
        {risk.description}
      </div>
    </div>
  )
}
