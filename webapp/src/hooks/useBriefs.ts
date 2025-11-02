/**
 * Custom hooks pour les Market Briefs
 */

import { useQuery } from '@tanstack/react-query'
import { briefService } from '@/services'
import type { BriefFilters, MarketBrief } from '@/types'

/**
 * Hook pour récupérer la liste des briefs
 */
export function useBriefs(filters?: BriefFilters) {
  return useQuery({
    queryKey: ['briefs', 'list', filters],
    queryFn: () => briefService.getBriefs(filters),
    staleTime: 15 * 60 * 1000, // 15 minutes
  })
}

/**
 * Hook pour récupérer un brief spécifique
 */
export function useBrief(id: string) {
  return useQuery({
    queryKey: ['briefs', 'detail', id],
    queryFn: () => briefService.getBrief(id),
    enabled: !!id,
    staleTime: 30 * 60 * 1000,
  })
}

/**
 * Hook pour récupérer le dernier brief
 */
export function useLatestBrief(type: 'daily' | 'weekly' = 'daily', universe: string[] = ['SPY', 'QQQ']) {
  return useQuery({
    queryKey: ['briefs', 'latest', type, universe],
    queryFn: () => briefService.getLatest(type, universe),
    staleTime: 5 * 60 * 1000,
  })
}
