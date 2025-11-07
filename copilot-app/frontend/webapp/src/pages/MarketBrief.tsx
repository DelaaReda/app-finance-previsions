/**
 * Page Market Brief
 * Daily/Weekly briefs avec Top 3 signaux/risques
 */

import { useState } from 'react'
import { useLatestBriefWithFallback } from '@/hooks/useBriefs'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import TopSignals from '@/components/signals/TopSignals'
import TopRisks from '@/components/signals/TopRisks'
import FreshnessBadge from '@/components/ui/FreshnessBadge'
import { ensureArray } from '@/lib/safe'

export default function MarketBrief() {
  const [type, setType] = useState<'daily' | 'weekly'>('daily')
  const [universe, setUniverse] = useState<string[]>(['SPY', 'QQQ'])
  
  // Use the fallback-aware hook with callback for fallback detection
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null)
  const { data: briefResp, isLoading, error } = useLatestBriefWithFallback(
    type, 
    universe,
    (message) => setFallbackMessage(message)
  )
  
  const brief = briefResp?.data || briefResp || {}  // Handle both nested and flat response
  
  // Check if response contains fallback indicators
  const hasFallback = fallbackMessage != null || 
    brief.is_fallback || 
    brief.fallback || 
    brief.error || 
    ('top_signals' in brief && Array.isArray(brief.top_signals) && brief.top_signals.length === 0 && 
     'top_risks' in brief && Array.isArray(brief.top_risks) && brief.top_risks.length === 0)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>📋 Market Brief</h1>
        
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <FreshnessBadge freshness={brief?.generated_at ?? brief?.freshness ?? undefined} />
          
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
      
      {/* Fallback banner if needed */}
      {hasFallback && fallbackMessage && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#4a5568',
          color: '#fff',
          borderRadius: '0.5rem',
          marginBottom: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div>
            <strong style={{ color: '#fbbd23' }}>⚠️ {fallbackMessage}</strong> • 
            Dernière mise à jour du système: {new Date(brief?.generated_at || brief?.freshness || Date.now()).toLocaleTimeString()}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              backgroundColor: '#2d3748',
              border: '1px solid #4a5568',
              color: '#fff',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Réessayer
          </button>
        </div>
      )}
      
      {!isLoading && !error && brief && Object.keys(brief).length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <Card>
            <h2 style={{ margin: '0 0 1rem 0' }}>Market Brief {brief.period === 'daily' ? 'Journalier' : 'Hebdomadaire'}</h2>
            <div style={{ color: '#888', marginBottom: '1rem' }}>
              {brief.generated_at || brief.freshness ? 
                new Date(brief.generated_at || brief.freshness).toLocaleDateString('fr-FR', {
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
              Analyse générée pour l'univers: {ensureArray(brief.universe || universe).join(', ')}
            </div>
          </Card>
          
          {/* Summary content if available - for better UX */}
          {(brief.summary || brief.content) && (
            <Card>
              <h3 style={{ margin: '0 0 1rem 0' }}>Résumé</h3>
              <div style={{ lineHeight: 1.6, color: '#ccc' }}>
                {brief.summary || brief.content}
              </div>
            </Card>
          )}

          {/* Top 3 Signaux et Top 3 Risques */}
          <div style={{ display: 'grid', gap: '1.5rem', gridTemplateColumns: '1fr 1fr' }}>
            <TopSignals signals={ensureArray(brief?.top_signals || brief?.signals || [])} title="Top 3 Signaux" />
            <TopRisks risks={ensureArray(brief?.top_risks || brief?.risks || [])} title="Top 3 Risques" />
          </div>

          {/* Picks */}
          {brief?.picks && Array.isArray(brief.picks) && brief.picks.length > 0 && (
            <Card title="🎯 Picks">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {ensureArray(brief.picks).map((pick: any, index: number) => (
                  <div key={index} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: '0.5rem',
                    backgroundColor: '#1a1a1a',
                    borderRadius: '4px'
                  }}>
                    <div>
                      <strong>{pick.ticker || pick.symbol || pick.asset}</strong> - Score: {pick.composite_score?.toFixed(1) || pick.score?.toFixed(1) || 'N/A'}
                    </div>
                    <div style={{ 
                      padding: '0.25rem 0.5rem', 
                      borderRadius: '4px',
                      backgroundColor: pick.action === 'BUY' || pick.action === 'buy' || pick.direction === 'up' ? '#4caf50' : 
                                      pick.action === 'SELL' || pick.action === 'sell' || pick.direction === 'down' ? '#f44336' : '#2196f3',
                      color: 'white',
                      fontSize: '0.8rem'
                    }}>
                      {(pick.action || pick.direction || 'HOLD').toString().toUpperCase()}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Sources */}
          {brief?.sources && Array.isArray(brief.sources) && brief.sources.length > 0 && (
            <Card title="📚 Sources">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {ensureArray(brief.sources).map((source: any, index: number) => (
                  <span key={index} style={{ 
                    padding: '0.25rem 0.5rem', 
                    backgroundColor: '#333',
                    borderRadius: '12px',
                    fontSize: '0.8rem'
                  }}>
                    {source.type || source.name || source.id || 'N/A'}: {source.series_id || source.count || source.id || 'N/A'}
                  </span>
                ))}
              </div>
            </Card>
          )}

          <div style={{ fontSize: '0.85rem', color: '#666', textAlign: 'center' }}>
            Généré le {brief?.generated_at || brief?.freshness ? new Date(brief.generated_at || brief.freshness).toLocaleString() : 'N/A'} • Période: {brief?.period || type || 'N/A'}
          </div>
        </div>
      )}
      
      {/* Empty state when no data and no loading/error */}
      {!isLoading && !error && (!brief || Object.keys(brief).length === 0) && (
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center', 
          padding: '40px 20px',
          textAlign: 'center',
          border: '1px dashed #ddd',
          borderRadius: '8px',
          backgroundColor: '#fafafa',
          minHeight: '200px',
          marginTop: '20px'
        }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#666' }}>Aucun brief disponible</h3>
          <p style={{ margin: '5px 0 0 0', color: '#888' }}>Le système est en train de générer le brief de marché</p>
        </div>
      )}
    </div>
  )
}
