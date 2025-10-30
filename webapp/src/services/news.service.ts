// webapp/src/services/news.service.ts
import { apiGet } from '../api/client'
import type { NewsFeed, NewsSentiment } from '../types/news.types'

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
  }
}
