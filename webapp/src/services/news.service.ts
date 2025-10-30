// Service pour le pilier News

import { apiGet } from './api'
import { NewsArticle, NewsFeed, NewsFilters, NewsAggregation } from '@/types/news.types'
import type { ApiResult } from './api'

export const newsService = {
  // Flux de news avec filtres
  getFeed: async (filters?: NewsFilters, page: number = 1, pageSize: number = 20): Promise<ApiResult<NewsFeed>> => {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize)
    }
    
    if (filters?.tickers) params.tickers = filters.tickers.join(',')
    if (filters?.sources) params.sources = filters.sources.join(',')
    if (filters?.sentiment) params.sentiment = filters.sentiment
    if (filters?.dateFrom) params.date_from = filters.dateFrom
    if (filters?.dateTo) params.date_to = filters.dateTo
    if (filters?.minScore) params.min_score = String(filters.minScore)
    if (filters?.tags) params.tags = filters.tags.join(',')

    return apiGet<NewsFeed>('/news/feed', params)
  },

  // Article spécifique
  getArticle: async (id: string): Promise<ApiResult<NewsArticle>> => {
    return apiGet<NewsArticle>(`/news/${id}`)
  },

  // Agrégation news par ticker
  getTickerAggregation: async (ticker: string): Promise<ApiResult<NewsAggregation>> => {
    return apiGet<NewsAggregation>(`/news/ticker/${ticker}/aggregation`)
  },
  // Top news du jour
  getTodayTop: async (limit: number = 10): Promise<ApiResult<NewsArticle[]>> => {
    return apiGet<NewsArticle[]>('/news/today/top', { limit: String(limit) })
  },

  // Sources disponibles
  getSources: async (): Promise<ApiResult<string[]>> => {
    return apiGet<string[]>('/news/sources')
  },

  // Tendances/topics
  getTrends: async (): Promise<ApiResult<Array<{ topic: string; count: number }>>> => {
    return apiGet('/news/trends')
  }
}
