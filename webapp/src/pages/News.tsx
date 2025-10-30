/**
 * Page News - Pilier 3
 * RSS robuste + scoring fraîcheur/source/pertinence
 */

import { useState } from 'react'
import { useNewsFeed } from '@/hooks/useNews'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'
import type { NewsFilters, NewsItem } from '@/types'

export default function News() {
  const [filters, setFilters] = useState<NewsFilters>({})
  const { data, isLoading, error } = useNewsFeed(filters, 1, 20)

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>📰 News Feed</h1>
      
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
          <select
            value={filters.sentiment || 'all'}
            onChange={(e) => setFilters({ ...filters, sentiment: e.target.value as any })}
            style={{
              padding: '0.5rem',
              backgroundColor: '#1a1a1a',
              border: '1px solid #333',
              borderRadius: '6px',
              color: '#fff',
            }}
          >
            <option value="all">Tous les sentiments</option>
            <option value="positive">Positif</option>
            <option value="neutral">Neutre</option>
            <option value="negative">Négatif</option>
          </select>
        </div>
      </div>

      {isLoading && <LoadingSpinner message="Chargement des news..." />}
      {error && <ErrorMessage error={error as Error} />}
      
      {data && (
        <div>
          <div style={{ marginBottom: '1rem', color: '#888' }}>
            {data.total} articles • Page {data.page}
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {data.items.map((item) => (
              <NewsCard key={item.id} news={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
function NewsCard({ news }: { news: NewsItem }) {
  const sentimentColor = news.sentiment === 'positive' ? '#4ade80' : news.sentiment === 'negative' ? '#f87171' : '#94a3b8'
  
  return (
    <Card
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
          <span>{news.source.name}</span>
          <span>{new Date(news.published_at).toLocaleString()}</span>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <a
          href={news.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontSize: '1.1rem',
            fontWeight: 600,
            color: '#4a9eff',
            textDecoration: 'none',
          }}
        >
          {news.title}
        </a>
        
        <p style={{ margin: 0, color: '#ccc', lineHeight: 1.6 }}>
          {news.summary}
        </p>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{
            padding: '0.25rem 0.75rem',
            backgroundColor: sentimentColor + '22',
            color: sentimentColor,
            borderRadius: '12px',
            fontSize: '0.85rem',
            fontWeight: 600,
          }}>
            {news.sentiment}
          </span>
          
          <span style={{ fontSize: '0.85rem', color: '#888' }}>
            Score: {news.composite_score.toFixed(1)}
          </span>

          {news.tickers.length > 0 && (
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {news.tickers.slice(0, 3).map((ticker) => (
                <span
                  key={ticker}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: '#1a2a3a',
                    color: '#6a9aef',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                  }}
                >
                  {ticker}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}
