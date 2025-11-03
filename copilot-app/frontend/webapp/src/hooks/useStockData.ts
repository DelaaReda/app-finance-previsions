/**
 * Custom hooks pour les données actions
 * Utilise React Query pour le caching
 */

import { useQuery } from '@tanstack/react-query'
import { stocksService } from '@/services'

/**
 * Hook pour récupérer l'analyse complète d'une action
 */
export function useStockAnalysis(ticker: string) {
  return useQuery({
    queryKey: ['stocks', ticker, 'analysis'],
    queryFn: () => stocksService.getAnalysis(ticker),
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook pour récupérer les indicateurs techniques
 */
export function useTechnicalIndicators(ticker: string) {
  return useQuery({
    queryKey: ['stocks', ticker, 'technical'],
    queryFn: async () => {
      const detail = await stocksService.getTickerDetail(ticker)
      return detail
    },
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000,
  })
}
