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
      
      // Ensure we return a consistent structure regardless of backend response format
      if (response.ok && response.data) {
        const rawData = response.data;
        
        // Handle different possible response structures
        let briefData;
        if (rawData && typeof rawData === 'object') {
          if ('data' in rawData && rawData.data) {
            // If response is { ok: true, data: { ... } }
            briefData = rawData.data;
          } else {
            // Direct response object
            briefData = rawData;
          }
        } else {
          // Fallback to empty object
          briefData = {};
        }
        
        // Check for fallback indicators in the processed data
        const hasSignals = briefData.top_signals && Array.isArray(briefData.top_signals) && briefData.top_signals.length > 0;
        const hasRisks = briefData.top_risks && Array.isArray(briefData.top_risks) && briefData.top_risks.length > 0;
        
        if (briefData.is_fallback || briefData.fallback || briefData.error || (!hasSignals && !hasRisks)) {
          // Déclencher le callback si fourni
          if (onFallbackDetected) {
            const fallbackReason = briefData.fallback_reason || 
              briefData.error || 
              (!hasSignals && !hasRisks ? 'Signaux et risques absents' : 'Fonctionalité de secours active')
            onFallbackDetected(fallbackReason)
          }
        }
        
        // Return processed data in a consistent format
        return {
          ok: true,
          data: briefData
        };
      }
      
      return response;
    },
    staleTime: 5 * 60 * 1000,
  })
}
