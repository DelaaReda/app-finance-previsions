/**
 * Page Stocks - Pilier 2
 * Actions, indicateurs techniques, comparaisons secteurs
 */

import { useState } from 'react'
import { useStockAnalysis } from '@/hooks/useStockData'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function Stocks() {
  const [ticker, setTicker] = useState('AAPL')
  const [inputTicker, setInputTicker] = useState('AAPL')
  
  const { data, isLoading, error } = useStockAnalysis(ticker)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setTicker(inputTicker.toUpperCase())
  }

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>📈 Actions & Indicateurs</h1>
      
      {/* Barre de recherche */}
      <form onSubmit={handleSearch} style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', maxWidth: '500px' }}>
          <input
            type="text"
            value={inputTicker}
            onChange={(e) => setInputTicker(e.target.value)}
            placeholder="Ticker (ex: AAPL, TSLA, MSFT)"
            style={{
              flex: 1,
              padding: '0.75rem',
              backgroundColor: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: '6px',
              color: '#fff',
              fontSize: '1rem',
            }}
          />
          <button
            type="submit"
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#4a9eff',
              border: 'none',
              borderRadius: '6px',
              color: '#fff',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Rechercher
          </button>
        </div>
      </form>

      {isLoading && <LoadingSpinner message={`Chargement de ${ticker}...`} />}
      {error && <ErrorMessage error={error as Error} />}
      
      {data && <StockAnalysisView analysis={data} />}
    </div>
  )
}
import type { StockAnalysis } from '@/types'

function StockAnalysisView({ analysis }: { analysis: StockAnalysis }) {
  return (
    <div style={{ display: 'grid', gap: '1.5rem' }}>
      {/* Info principale */}
      <Card>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
          <div>
            <h2 style={{ margin: 0 }}>{analysis.ticker}</h2>
            <div style={{ color: '#888', marginTop: '0.25rem' }}>
              {analysis.name} • {analysis.sector}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              ${analysis.current_price.toFixed(2)}
            </div>
            <div style={{
              color: analysis.change_pct >= 0 ? '#4ade80' : '#f87171',
              fontWeight: 600,
            }}>
              {analysis.change_pct >= 0 ? '+' : ''}{analysis.change_pct.toFixed(2)}%
            </div>
          </div>
        </div>
      </Card>

      {/* Score composite */}
      <Card title="Score Composite (40/40/20)">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
          <ScoreItem label="Macro" value={analysis.score.macro} />
          <ScoreItem label="Technique" value={analysis.score.technical} />
          <ScoreItem label="News" value={analysis.score.news} />
          <ScoreItem label="Composite" value={analysis.score.composite} highlight />
        </div>
      </Card>
    </div>
  )
}

function ScoreItem({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div style={{
      padding: '0.75rem',
      backgroundColor: highlight ? '#1a2a3a' : '#1a1a1a',
      borderRadius: '6px',
      border: highlight ? '1px solid #4a9eff' : '1px solid #333',
    }}>
      <div style={{ fontSize: '0.85rem', color: '#888', marginBottom: '0.25rem' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: highlight ? '#4a9eff' : '#fff' }}>
        {value.toFixed(1)}
      </div>
    </div>
  )
}
