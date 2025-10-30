/**
 * Service API pour le Pilier 3: NEWS
 * Gestion des news RSS, scoring, filtrage
 */

import { apiGet, apiPost } from '@/api/client'
import type { NewsFeed, NewsItem, NewsFilters } from '@/types'

export const newsService = {
  /**
   * Récupère le feed de news avec filtres
   */
  getNewsFeed: async (filters?: NewsFilters, page = 1, pageSize = 20): Promise<NewsFeed> => {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize),
    }
    
    if (filters?.tickers?.length) params.tickers = filters.tickers.join(',')
    if (filters?.topics?.length) params.topics = filters.topics.join(',')
    if (filters?.sentiment && filters.sentiment !== 'all') params.sentiment = filters.sentiment
    if (filters?.date_from) params.date_from = filters.date_from
    if (filters?.date_to) params.date_to = filters.date_to
    if (filters?.min_score) params.min_score = String(filters.min_score)

    const result = await apiGet<NewsFeed>('/news/feed', params)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Récupère une news spécifique
   */
  getNewsItem: async (id: string): Promise<NewsItem> => {
    const result = await apiGet<NewsItem>(`/news/${id}`)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },
}
