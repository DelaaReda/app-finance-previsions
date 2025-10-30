/**
 * Custom hooks pour les news
 */

import { useQuery } from '@tanstack/react-query'
import { newsService } from '@/services'
import type { NewsFilters, NewsFeed, NewsItem } from '@/types'

/**
 * Hook pour récupérer le feed de news
 */
export function useNewsFeed(filters?: NewsFilters, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['news', 'feed', filters, page, pageSize],
    queryFn: () => newsService.getNewsFeed(filters, page, pageSize),
    staleTime: 2 * 60 * 1000, // 2 minutes (news fraiches)
  })
}

/**
 * Hook pour récupérer une news spécifique
 */
export function useNewsItem(id: string) {
  return useQuery({
    queryKey: ['news', 'item', id],
    queryFn: () => newsService.getNewsItem(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  })
}
