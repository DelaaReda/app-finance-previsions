/**
 * Custom hooks pour les données macro
 * Utilise React Query pour le caching et la gestion d'état
 */

import { useQuery } from '@tanstack/react-query'
import { macroService } from '@/services'
import type { MacroDashboard, MacroSeries, MacroIndicator } from '@/types'

/**
 * Hook pour récupérer le dashboard macro complet
 */
export function useMacroDashboard() {
  return useQuery({
    queryKey: ['macro', 'dashboard'],
    queryFn: () => macroService.getDashboard(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // Rafraîchir toutes les 10 minutes
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
export function useMacroIndicator(indicatorId: string) {
  return useQuery({
    queryKey: ['macro', 'indicator', indicatorId],
    queryFn: () => macroService.getIndicator(indicatorId),
    enabled: !!indicatorId,
    staleTime: 5 * 60 * 1000,
  })
}
