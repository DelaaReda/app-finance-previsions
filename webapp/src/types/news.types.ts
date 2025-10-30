/**
 * Types pour le Pilier 3: NEWS
 * RSS robuste + scoring fraîcheur/source/pertinence
 */

import { Source } from './common.types'

export type NewsItem = {
  id: string
  title: string
  summary: string
  content?: string
  url: string
  source: Source
  published_at: string
  ingested_at: string
  tickers: string[]
  topics: string[]
  sentiment: 'positive' | 'negative' | 'neutral'
  sentiment_score: number
  relevance_score: number
  freshness_score: number
  source_quality_score: number
  composite_score: number
  hash: string // Pour déduplication (source|title|published)
  language: string
}

export type NewsScore = {
  freshness: number      // 0-100, basé sur l'âge
  source_quality: number // 0-100, basé sur la réputation
  relevance: number      // 0-100, pertinence ticker/topic
  composite: number      // Score final pondéré
}

export type NewsFeed = {
  items: NewsItem[]
  total: number
  page: number
  page_size: number
  filters: NewsFilters
  last_updated: string
}

export type NewsFilters = {
  tickers?: string[]
  topics?: string[]
  sentiment?: 'positive' | 'negative' | 'neutral' | 'all'
  sources?: string[]
  date_from?: string
  date_to?: string
  min_score?: number
}
