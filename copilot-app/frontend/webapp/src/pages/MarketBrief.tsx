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
import { FreshnessBadge } from '@/components/ui/FreshnessBadge'

export default function MarketBrief() {
  const [type, setType] = useState<'daily' | 'weekly'>('daily')
  const [universe, setUniverse] = useState<string[]>(['SPY', 'QQQ'])
  const { data: briefResp, isLoading, error } = useLatestBrief(type, universe)
  const brief = briefResp?.data as any

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>📋 Market Brief</h1>
        
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <FreshnessBadge 
            freshness={brief?.generated_at || null} 
            stale={brief?.generated_at ? new Date().getTime() - new Date(brief.generated_at).getTime() > 3600000 : false} 
          />
          
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
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label htmlFor="universe-select">Univers:</label>
            <select
              id="universe-select"
              value={universe?.join(',') || 'SPY,QQQ'}
              onChange={(e) => setUniverse(e.target.value ? e.target.value.split(',') : ['SPY', 'QQQ'])}
              style={{
                padding: '0.5rem',
                backgroundColor: '#333',
                border: '1px solid #444',
                borderRadius: '4px',
                color: '#fff',
              }}
            >
              <option value="SPY,QQQ">SPY,QQQ (Défaut)</option>
              <option value="SPY,AAPL,NVDA,MSFT">SPY,AAPL,NVDA,MSFT</option>
              <option value="QQQ,AAPL,GOOGL,AMZN">QQQ,AAPL,GOOGL,AMZN</option>
              <option value="SPY,TSLA,META,NVDA">SPY,TSLA,META,NVDA</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading && <LoadingSpinner />}
      {error && <ErrorMessage message={String(error)} />}
      
      {brief && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <Card>
            <h2 style={{ margin: '0 0 1rem 0' }}>Market Brief {brief.period === 'daily' ? 'Journalier' : 'Hebdomadaire'}</h2>
            <div style={{ color: '#888', marginBottom: '1rem' }}>
              {brief.generated_at ? 
                new Date(brief.generated_at).toLocaleDateString('fr-FR', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })
              : 'Date non disponible'}
            </div>
            <div style={{ lineHeight: 1.6 }}>
              Analyse générée pour l'univers: {(brief.universe || []).join(', ')}
            </div>
          </Card>
          {/* Top 3 Signaux et Top 3 Risques */}
          <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: '1fr 1fr' }}>
            <TopSignals signals={brief.top_signals || []} title="Top 3 Signaux" />
            <TopRisks risks={brief.top_risks || []} title="Top 3 Risques" />
          </div>

          {/* Picks */}
          {brief.picks && brief.picks.length > 0 && (
            <Card title="🎯 Picks">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {brief.picks.map((pick: any, index: number) => (
                  <div key={index} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '0.5rem',
                    backgroundColor: '#1a1a1a',
                    borderRadius: '4px'
                  }}>
                    <div>
                      <strong>{pick.ticker}</strong> - Score: {pick.composite_score?.toFixed(1) || pick.score?.toFixed(1) || 'N/A'}
                    </div>
                    <div style={{ 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '4px',
                      backgroundColor: pick.action === 'BUY' ? '#4caf50' : 
                                      pick.action === 'SELL' ? '#f44336' : '#2196f3',
                      color: 'white',
                      fontSize: '0.8rem'
                    }}>
                      {pick.action || 'HOLD'}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Sources */}
          {brief.sources && brief.sources.length > 0 && (
            <Card title="📚 Sources">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {brief.sources.map((source: any, index: number) => (
                  <span key={index} style={{ 
                    padding: '0.25rem 0.5rem', 
                    backgroundColor: '#333',
                    borderRadius: '12px',
                    fontSize: '0.8rem'
                  }}>
                    {source.type || source.meta?.type || 'N/A'}: {source.series_id || source.meta?.series_id || source.count || source.meta?.count || 'N/A'}
                  </span>
                ))}
              </div>
            </Card>
          )}

          <div style={{ fontSize: '0.85rem', color: '#666', textAlign: 'center' }}>
            Généré le {brief.generated_at ? new Date(brief.generated_at).toLocaleString() : 'N/A'} • Période: {brief.period || 'N/A'}
          </div>
        </div>
      )}
    </div>
  )
}
