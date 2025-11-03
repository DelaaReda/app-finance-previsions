/**
 * Custom hooks pour les données macro
 * Utilise React Query pour le caching et la gestion d'état
 */

import { useQuery } from '@tanstack/react-query'
import { macroService } from '@/services'

/**
 * Hook pour récupérer le dashboard macro complet
 */
export function useMacroSnapshot() {
  return useQuery({
    queryKey: ['macro', 'snapshot'],
    queryFn: () => macroService.getSnapshot(),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
  })
}

/**
 * Hook pour récupérer une série macro
 */
export function useMacroSeries(seriesId: string) {
  return useQuery({
    queryKey: ['macro', 'series', seriesId],
    queryFn: () => macroService.getSeries(seriesId),
    enabled: !!seriesId,
    staleTime: 15 * 60 * 1000, // 15 minutes
  })
}

/**
 * Hook pour récupérer un indicateur macro
 */
export function useMacroIndicators() {
  return useQuery({
    queryKey: ['macro', 'indicators'],
    queryFn: () => macroService.getIndicators(),
    staleTime: 5 * 60 * 1000,
  })
}
