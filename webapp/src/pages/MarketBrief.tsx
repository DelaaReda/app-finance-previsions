/**
 * Page Market Brief
 * Daily/Weekly briefs avec Top 3 signaux/risques
 */

import { useState } from 'react'
import { useLatestBrief } from '@/hooks/useBriefs'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import TopSignals from '@/components/signals/TopSignals'
import TopRisks from '@/components/signals/TopRisks'

export default function MarketBrief() {
  const [type, setType] = useState<'daily' | 'weekly'>('daily')
  const { data: brief, isLoading, error } = useLatestBrief(type)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>📋 Market Brief</h1>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setType('daily')}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: type === 'daily' ? '#4a9eff' : '#333',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            Quotidien
          </button>
          <button
            onClick={() => setType('weekly')}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: type === 'weekly' ? '#4a9eff' : '#333',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            Hebdomadaire
          </button>
        </div>
      </div>

      {isLoading && <LoadingSpinner message="Chargement du brief..." />}
      {error && <ErrorMessage error={error as Error} />}
      
      {brief && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <Card>
            <h2 style={{ margin: '0 0 1rem 0' }}>{brief.title}</h2>
            <div style={{ color: '#888', marginBottom: '1rem' }}>
              {new Date(brief.date).toLocaleDateString('fr-FR', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </div>
            <div style={{ lineHeight: 1.6 }}>
              {brief.executive_summary}
            </div>
          </Card>
          {/* Top 3 Signaux et Top 3 Risques */}
          <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: '1fr 1fr' }}>
            <TopSignals signals={brief.top_signals} />
            <TopRisks risks={brief.top_risks} />
          </div>

          {/* Snapshots par pilier */}
          <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
            <Card title="📊 Macro">
              <div style={{ marginBottom: '0.75rem', fontWeight: 600 }}>
                {brief.macro_snapshot.headline}
              </div>
              <div style={{ color: '#888', fontSize: '0.9rem' }}>
                Tendance: <span style={{
                  color: brief.macro_snapshot.trend === 'bullish' ? '#4ade80' : brief.macro_snapshot.trend === 'bearish' ? '#f87171' : '#94a3b8',
                  fontWeight: 600,
                }}>
                  {brief.macro_snapshot.trend}
                </span>
              </div>
            </Card>

            <Card title="📈 Marchés">
              <div style={{ marginBottom: '0.75rem', fontWeight: 600 }}>
                {brief.market_snapshot.headline}
              </div>
              <div style={{ color: '#888', fontSize: '0.9rem' }}>
                Sentiment: <span style={{
                  color: brief.market_snapshot.market_sentiment === 'bullish' ? '#4ade80' : brief.market_snapshot.market_sentiment === 'bearish' ? '#f87171' : '#94a3b8',
                  fontWeight: 600,
                }}>
                  {brief.market_snapshot.market_sentiment}
                </span>
              </div>
            </Card>

            <Card title="📰 News">
              <div style={{ marginBottom: '0.75rem', fontWeight: 600 }}>
                {brief.news_snapshot.headline}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#888' }}>
                {brief.news_snapshot.top_stories.length} articles majeurs
              </div>
            </Card>
          </div>

          {/* Key Takeaways */}
          {brief.key_takeaways && brief.key_takeaways.length > 0 && (
            <Card title="🎯 Points clés">
              <ul style={{ margin: 0, paddingLeft: '1.5rem', lineHeight: 1.8 }}>
                {brief.key_takeaways.map((takeaway, idx) => (
                  <li key={idx}>{takeaway}</li>
                ))}
              </ul>
            </Card>
          )}

          <div style={{ fontSize: '0.85rem', color: '#666', textAlign: 'center' }}>
            Généré le {new Date(brief.generated_at).toLocaleString()} • Version {brief.version}
          </div>
        </div>
      )}
    </div>
  )
}
