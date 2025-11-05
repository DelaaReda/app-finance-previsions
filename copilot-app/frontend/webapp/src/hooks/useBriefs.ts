/**
 * Custom hooks pour les Market Briefs
 */

import { useQuery } from '@tanstack/react-query'
import { briefService } from '@/services'
import type { BriefFilters } from '@/types/brief.types'

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

/**
 * Hook pour récupérer le dernier brief avec détection de fallback
 */
export function useLatestBriefWithFallback(type: 'daily' | 'weekly' = 'daily', universe: string[] = ['SPY', 'QQQ'], onFallbackDetected?: (message: string) => void) {
  return useQuery({
    queryKey: ['briefs', 'latest-with-fallback', type, universe],
    queryFn: async () => {
      const response = await briefService.getLatest(type, universe)
      
      if (response.ok && response.data) {
        const briefData = response.data
        // Vérifier si le brief contient des indicateurs de fallback
        if (briefData.is_fallback || briefData.fallback || briefData.error || (briefData.top_signals?.length === 0 && briefData.top_risks?.length === 0)) {
          // Déclencher le callback si fourni
          if (onFallbackDetected) {
            const fallbackReason = briefData.fallback_reason || 
              briefData.error || 
              (briefData.top_signals?.length === 0 && briefData.top_risks?.length === 0 ? 'Signaux et risques absents' : 'Fonctionalité de secours active')
            onFallbackDetected(fallbackReason)
          }
        }
      }
      
      return response
    },
    staleTime: 5 * 60 * 1000,
  })
}
