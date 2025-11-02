// webapp/src/services/news.service.ts
import { apiGet } from '../api/client'
import type { NewsFeed, NewsSentiment } from '../types/news.types'

export interface NewsFilters {
  ticker?: string
  region?: string
  limit?: number
  page?: number
  startDate?: string
  endDate?: string
  keywords?: string
}

export const newsService = {
  /**
   * Get news feed with scoring
   */
  getFeed: async (ticker?: string, region = 'all', limit = 50) => {
    const params: Record<string, string> = { region, limit: String(limit) }
    if (ticker) params.ticker = ticker
    return apiGet<NewsFeed>('/news/feed', params)
  },

  /**
   * Get aggregated sentiment by ticker
   */
  getSentiment: async () => {
    return apiGet<NewsSentiment>('/news/sentiment')
  },

  /**
   * Get news feed with filters (alias for hooks)
   */
  getNewsFeed: async (filters?: NewsFilters, page = 1, pageSize = 20) => {
    const params: Record<string, string> = {
      limit: String(pageSize),
      since: '7d', // Default to 7 days
      ...filters,
    }
    
    // If filters has ticker, use it
    if (filters?.ticker) params.ticker = filters.ticker
    if (filters?.region) params.region = filters.region
    if (filters?.startDate) params.start = filters.startDate
    if (filters?.endDate) params.end = filters.endDate
    if (filters?.keywords) params.q = filters.keywords
    
    return apiGet<NewsFeed>('/news/feed', params)
  },

  /**
   * Get specific news item (placeholder - API may not support this yet)
   */
  getNewsItem: async (id: string) => {
    // For now, this returns an error since the backend may not have a single news item endpoint
    // In a real implementation, this would call `/api/news/item/${id}` or similar
    return { ok: false, error: "Single news item endpoint not implemented yet" } as const
  }
}
