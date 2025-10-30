// Types pour le pilier News (RSS, scoring, sentiment)

import { Source } from './common.types'

export type NewsArticle = {
  id: string
  title: string
  summary: string
  content?: string
  url: string
  source: Source
  publishedAt: string
  author?: string
  tags: string[]
  tickers: string[] // Tickers mentionnés
  sentiment: Sentiment
  score: NewsScore
  language: string
  imageUrl?: string
}

export type Sentiment = {
  polarity: 'positive' | 'negative' | 'neutral'
  score: number // -1 à 1
  confidence: number // 0 à 1
}

export type NewsScore = {
  freshness: number // 0-100, basé sur l'âge
  sourceReliability: number // 0-100
  relevance: number // 0-100, pertinence pour le ticker
  composite: number // Score final (20% dans score global)
}
export type NewsFeed = {
  articles: NewsArticle[]
  total: number
  page: number
  pageSize: number
  filters: NewsFilters
  lastUpdate: string
}

export type NewsFilters = {
  tickers?: string[]
  sources?: string[]
  sentiment?: 'positive' | 'negative' | 'neutral'
  dateFrom?: string
  dateTo?: string
  minScore?: number
  tags?: string[]
}

export type NewsAggregation = {
  ticker: string
  articlesCount: number
  averageSentiment: number
  sentimentTrend: 'improving' | 'declining' | 'stable'
  topTopics: string[]
  lastUpdate: string
}
