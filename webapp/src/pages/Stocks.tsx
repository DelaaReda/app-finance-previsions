// Page Stocks - Pilier 2: Actions + Indicateurs Techniques

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { stocksService } from '@/services/stocks.service'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function Stocks() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null)

  // Recherche d'actions
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['stocks-search', searchQuery],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return []
      const result = await stocksService.search(searchQuery)
      return result.ok ? result.data : []
    },
    enabled: searchQuery.length >= 2,
  })

  // Analyse du ticker sélectionné
  const { data: analysis, isLoading: isLoadingAnalysis } = useQuery({
    queryKey: ['stock-analysis', selectedTicker],
    queryFn: async () => {
      if (!selectedTicker) return null
      const result = await stocksService.getAnalysis(selectedTicker)
      return result.ok ? result.data : null
    },
    enabled: !!selectedTicker,
  })

  return (
    <MainLayout>
      <div style={styles.container}>
        <h2 style={styles.pageTitle}>📈 Actions - Analyse Technique</h2>

        {/* Barre de recherche */}
        <Card title="Rechercher une action">
          <input
            type="text"
            placeholder="Ticker ou nom (ex: AAPL, Apple)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={styles.searchInput}
          />
          
          {isSearching && <LoadingSpinner size={24} />}
          
          {searchResults && searchResults.length > 0 && (
            <div style={styles.resultsList}>
              {searchResults.map((stock) => (
                <div
                  key={stock.ticker}
                  style={styles.resultItem}
                  onClick={() => {
                    setSelectedTicker(stock.ticker)
                    setSearchQuery('')
                  }}
                >
                  <div style={styles.resultTicker}>{stock.ticker}</div>
                  <div style={styles.resultName}>{stock.name}</div>
                  <div style={stock.changePercent >= 0 ? styles.changePositive : styles.changeNegative}>
                    {stock.changePercent >= 0 ? '↗' : '↘'} {Math.abs(stock.changePercent).toFixed(2)}%
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Analyse du ticker sélectionné */}
        {selectedTicker && (
          <>
            {isLoadingAnalysis && <LoadingSpinner />}
            
            {analysis && (
              <div style={styles.analysisContainer}>
                {/* Info stock */}
                <Card title={`${analysis.stock.ticker} - ${analysis.stock.name}`}>
                  <div style={styles.stockInfo}>
                    <div style={styles.priceContainer}>
                      <div style={styles.price}>${analysis.stock.price.toFixed(2)}</div>
                      <div style={analysis.stock.changePercent >= 0 ? styles.changePositive : styles.changeNegative}>
                        {analysis.stock.change >= 0 ? '+' : ''}{analysis.stock.change.toFixed(2)} 
                        ({analysis.stock.changePercent.toFixed(2)}%)
                      </div>
                    </div>
                    <div style={styles.stockMeta}>
                      <span>Secteur: {analysis.stock.sector}</span>
                      <span>Volume: {(analysis.stock.volume / 1000000).toFixed(2)}M</span>
                    </div>
                  </div>
                </Card>

                {/* Score composite */}
                <Card title="Score Composite">
                  <div style={styles.scoreGrid}>
                    <div style={styles.scoreItem}>
                      <div style={styles.scoreLabel}>Macro</div>
                      <div style={styles.scoreValue}>{analysis.score.macro.toFixed(0)}/40</div>
                    </div>
                    <div style={styles.scoreItem}>
                      <div style={styles.scoreLabel}>Technique</div>
                      <div style={styles.scoreValue}>{analysis.score.technical.toFixed(0)}/40</div>
                    </div>
                    <div style={styles.scoreItem}>
                      <div style={styles.scoreLabel}>News</div>
                      <div style={styles.scoreValue}>{analysis.score.news.toFixed(0)}/20</div>
                    </div>
                    <div style={styles.scoreItem}>
                      <div style={styles.scoreLabel}>Total</div>
                      <div style={{ ...styles.scoreValue, color: '#4caf50', fontSize: 28 }}>
                        {analysis.score.composite.toFixed(0)}/100
                      </div>
                    </div>
                  </div>
                </Card>

                {/* Indicateurs techniques */}
                <Card title="Indicateurs Techniques">
                  <div style={styles.techGrid}>
                    <div style={styles.techItem}>
                      <span>SMA 20</span>
                      <span>${analysis.technicals.sma20.toFixed(2)}</span>
                    </div>
                    <div style={styles.techItem}>
                      <span>SMA 50</span>
                      <span>${analysis.technicals.sma50.toFixed(2)}</span>
                    </div>
                    <div style={styles.techItem}>
                      <span>SMA 200</span>
                      <span>${analysis.technicals.sma200.toFixed(2)}</span>
                    </div>
                    <div style={styles.techItem}>
                      <span>RSI</span>
                      <span style={getRSIColor(analysis.technicals.rsi)}>
                        {analysis.technicals.rsi.toFixed(1)}
                      </span>
                    </div>
                  </div>
                </Card>

                {/* Signaux */}
                {analysis.signals && analysis.signals.length > 0 && (
                  <Card title="Signaux Techniques">
                    <div style={styles.signalsList}>
                      {analysis.signals.map((signal, index) => (
                        <div key={index} style={getSignalStyle(signal.type)}>
                          <div style={styles.signalHeader}>
                            <span style={styles.signalType}>{signal.type.toUpperCase()}</span>
                            <span style={styles.signalStrength}>{signal.strength}/100</span>
                          </div>
                          <div style={styles.signalIndicator}>{signal.indicator}</div>
                          <div style={styles.signalDescription}>{signal.description}</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </MainLayout>
  )
}

function getRSIColor(rsi: number) {
  if (rsi > 70) return { color: '#f44336', fontWeight: 600 }
  if (rsi < 30) return { color: '#4caf50', fontWeight: 600 }
  return { color: '#ffb74d' }
}

function getSignalStyle(type: 'buy' | 'sell' | 'hold') {
  const colors = {
    buy: { bg: '#1a2a1a', border: '#2a4a2a' },
    sell: { bg: '#2a1515', border: '#4a2020' },
    hold: { bg: '#1a1a1a', border: '#2a2a2a' },
  }
  return {
    padding: 12,
    borderRadius: 6,
    marginBottom: 8,
    backgroundColor: colors[type].bg,
    border: `1px solid ${colors[type].border}`,
  }
}

const styles = {
  container: { display: 'flex', flexDirection: 'column' as const, gap: 24 },
  pageTitle: { margin: 0, fontSize: 28, fontWeight: 700, color: '#fff' },
  searchInput: {
    width: '100%',
    padding: 12,
    backgroundColor: '#222',
    border: '1px solid #444',
    borderRadius: 6,
    color: '#fff',
    fontSize: 14,
  },
  resultsList: { marginTop: 12, display: 'flex', flexDirection: 'column' as const, gap: 8 },
  resultItem: {
    padding: 12,
    backgroundColor: '#222',
    borderRadius: 6,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    transition: 'background-color 0.2s',
  },
  resultTicker: { fontSize: 14, fontWeight: 600, color: '#4caf50' },
  resultName: { flex: 1, fontSize: 14, color: '#ccc' },
  changePositive: { fontSize: 14, color: '#4caf50', fontWeight: 600 },
  changeNegative: { fontSize: 14, color: '#f44336', fontWeight: 600 },
  analysisContainer: { display: 'flex', flexDirection: 'column' as const, gap: 16 },
  stockInfo: { display: 'flex', flexDirection: 'column' as const, gap: 12 },
  priceContainer: { display: 'flex', alignItems: 'baseline', gap: 12 },
  price: { fontSize: 32, fontWeight: 700, color: '#fff' },
  stockMeta: { display: 'flex', gap: 24, fontSize: 13, color: '#999' },
  scoreGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
    gap: 16,
  },
  scoreItem: { textAlign: 'center' as const },
  scoreLabel: { fontSize: 12, color: '#999', marginBottom: 8 },
  scoreValue: { fontSize: 24, fontWeight: 700, color: '#fff' },
  techGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
    gap: 12,
  },
  techItem: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: 8,
    backgroundColor: '#222',
    borderRadius: 4,
  },
  signalsList: { display: 'flex', flexDirection: 'column' as const },
  signalHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: 4 },
  signalType: { fontSize: 12, fontWeight: 600 },
  signalStrength: { fontSize: 12, fontWeight: 600, color: '#4caf50' },
  signalIndicator: { fontSize: 13, fontWeight: 500, marginBottom: 4 },
  signalDescription: { fontSize: 12, color: '#aaa' },
}
