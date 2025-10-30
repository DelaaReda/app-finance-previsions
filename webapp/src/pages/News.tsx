// Page News - Pilier 3: RSS + Scoring + Sentiment

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { newsService } from '@/services/news.service'
import { NewsFilters } from '@/types/news.types'
import MainLayout from '@/components/layout/MainLayout'
import Card from '@/components/common/Card'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorMessage from '@/components/common/ErrorMessage'

export default function News() {
  const [filters, setFilters] = useState<NewsFilters>({})
  const [page, setPage] = useState(1)

  const { data: newsFeed, isLoading, error } = useQuery({
    queryKey: ['news-feed', filters, page],
    queryFn: async () => {
      const result = await newsService.getFeed(filters, page, 20)
      return result.ok ? result.data : null
    },
    staleTime: 60_000, // 1 minute
  })

  const { data: topNews } = useQuery({
    queryKey: ['news-top-today'],
    queryFn: async () => {
      const result = await newsService.getTodayTop(5)
      return result.ok ? result.data : []
    },
    staleTime: 120_000, // 2 minutes
  })

  if (isLoading) return <MainLayout><LoadingSpinner /></MainLayout>
  if (error) return <MainLayout><ErrorMessage message={String(error)} /></MainLayout>

  return (
    <MainLayout>
      <div style={styles.container}>
        <h2 style={styles.pageTitle}>📰 News - Actualités Financières</h2>

        {/* Top News du jour */}
        {topNews && topNews.length > 0 && (
          <Card title="🔥 Top News du jour">
            <div style={styles.topNewsList}>
              {topNews.map((article) => (
                <a
                  key={article.id}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.topNewsItem}
                >
                  <div style={styles.topNewsHeader}>
                    <span style={getSentimentColor(article.sentiment.polarity)}>
                      {article.sentiment.polarity === 'positive' ? '📈' : 
                       article.sentiment.polarity === 'negative' ? '📉' : '➡️'}
                    </span>
                    <span style={styles.topNewsScore}>{article.score.composite.toFixed(0)}/100</span>
                  </div>
                  <h4 style={styles.topNewsTitle}>{article.title}</h4>
                  <p style={styles.topNewsSummary}>{article.summary}</p>
                  <div style={styles.topNewsMeta}>
                    <span>{article.source.name}</span>
                    <span>{new Date(article.publishedAt).toLocaleString('fr-FR')}</span>
                  </div>
                </a>
              ))}
            </div>
          </Card>
        )}

        {/* Filtres */}
        <Card title="Filtres">
          <div style={styles.filtersGrid}>
            <input
              type="text"
              placeholder="Ticker (ex: AAPL, TSLA)"
              onChange={(e) => setFilters({...filters, tickers: e.target.value ? [e.target.value] : undefined})}
              style={styles.filterInput}
            />
            <select
              onChange={(e) => setFilters({...filters, sentiment: e.target.value as any || undefined})}
              style={styles.filterInput}
            >
              <option value="">Tous les sentiments</option>
              <option value="positive">Positif</option>
              <option value="negative">Négatif</option>
              <option value="neutral">Neutre</option>
            </select>
          </div>
        </Card>

        {/* Liste des articles */}
        {newsFeed && (
          <Card title={`Articles (${newsFeed.total} total)`}>
            <div style={styles.articlesList}>
              {newsFeed.articles.map((article) => (
                <a
                  key={article.id}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.articleItem}
                >
                  <div style={styles.articleHeader}>
                    <div style={styles.articleScores}>
                      <span style={getSentimentColor(article.sentiment.polarity)}>
                        {article.sentiment.polarity === 'positive' ? '📈' : 
                         article.sentiment.polarity === 'negative' ? '📉' : '➡️'}
                      </span>
                      <span style={styles.articleScore}>{article.score.composite.toFixed(0)}</span>
                    </div>
                    <span style={styles.articleSource}>{article.source.name}</span>
                  </div>
                  <h3 style={styles.articleTitle}>{article.title}</h3>
                  <p style={styles.articleSummary}>{article.summary}</p>
                  <div style={styles.articleFooter}>
                    <div style={styles.articleTickers}>
                      {article.tickers.slice(0, 3).map(ticker => (
                        <span key={ticker} style={styles.tickerTag}>{ticker}</span>
                      ))}
                    </div>
                    <span style={styles.articleDate}>
                      {new Date(article.publishedAt).toLocaleString('fr-FR')}
                    </span>
                  </div>
                </a>
              ))}
            </div>

            {/* Pagination */}
            <div style={styles.pagination}>
              <button
                disabled={page === 1}
                onClick={() => setPage(p => p - 1)}
                style={styles.paginationButton}
              >
                ← Précédent
              </button>
              <span style={styles.paginationInfo}>Page {page}</span>
              <button
                disabled={newsFeed.articles.length < 20}
                onClick={() => setPage(p => p + 1)}
                style={styles.paginationButton}
              >
                Suivant →
              </button>
            </div>
          </Card>
        )}
      </div>
    </MainLayout>
  )
}

function getSentimentColor(polarity: 'positive' | 'negative' | 'neutral') {
  const colors = {
    positive: { color: '#4caf50' },
    negative: { color: '#f44336' },
    neutral: { color: '#999' },
  }
  return colors[polarity]
}

const styles = {
  container: { display: 'flex', flexDirection: 'column' as const, gap: 24 },
  pageTitle: { margin: 0, fontSize: 28, fontWeight: 700, color: '#fff' },
  topNewsList: { display: 'flex', flexDirection: 'column' as const, gap: 16 },
  topNewsItem: {
    display: 'block',
    padding: 16,
    backgroundColor: '#222',
    borderRadius: 8,
    border: '1px solid #333',
    textDecoration: 'none',
    color: 'inherit',
    transition: 'transform 0.2s',
  },
  topNewsHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: 8 },
  topNewsScore: { fontSize: 14, fontWeight: 600, color: '#4caf50' },
  topNewsTitle: { margin: '0 0 8px', fontSize: 16, fontWeight: 600, color: '#fff' },
  topNewsSummary: { margin: '0 0 12px', fontSize: 13, color: '#aaa', lineHeight: 1.5 },
  topNewsMeta: { display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#666' },
  filtersGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 },
  filterInput: {
    padding: 10,
    backgroundColor: '#222',
    border: '1px solid #444',
    borderRadius: 6,
    color: '#fff',
    fontSize: 14,
  },
  articlesList: { display: 'flex', flexDirection: 'column' as const, gap: 12 },
  articleItem: {
    display: 'block',
    padding: 16,
    backgroundColor: '#1a1a1a',
    borderRadius: 6,
    border: '1px solid #2a2a2a',
    textDecoration: 'none',
    color: 'inherit',
  },
  articleHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  articleScores: { display: 'flex', alignItems: 'center', gap: 8 },
  articleScore: { fontSize: 13, fontWeight: 600, color: '#4caf50' },
  articleSource: { fontSize: 12, color: '#666' },
  articleTitle: { margin: '0 0 8px', fontSize: 15, fontWeight: 600, color: '#fff' },
  articleSummary: { margin: '0 0 12px', fontSize: 13, color: '#aaa', lineHeight: 1.5 },
  articleFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  articleTickers: { display: 'flex', gap: 6 },
  tickerTag: {
    padding: '2px 8px',
    backgroundColor: '#1a3a52',
    borderRadius: 4,
    fontSize: 11,
    color: '#64b5f6',
    fontWeight: 600,
  },
  articleDate: { fontSize: 11, color: '#666' },
  pagination: { display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16, marginTop: 16 },
  paginationButton: {
    padding: '8px 16px',
    backgroundColor: '#333',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    cursor: 'pointer',
    fontSize: 14,
  },
  paginationInfo: { fontSize: 14, color: '#999' },
}
