/**
 * Custom hooks pour le Copilot LLM
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import { client } from '@/api/client'
import { copilotService } from '@/services'
import type { CopilotAskRequest } from '@/types/copilot.types'

/**
 * Hook pour envoyer une query au copilot
 */
export function useCopilotQuery() {
  return useMutation({
    mutationFn: (query: CopilotAskRequest) => copilotService.ask(query),
  })
}

/**
 * Hook pour récupérer le contexte RAG disponible
 */
export function useRAGStats() {
  return useQuery({
    queryKey: ['copilot', 'rag', 'stats'],
    queryFn: () => copilotService.getRAGStats(),
    staleTime: 30 * 60 * 1000, // 30 minutes
  })
}

export function useCopilotContext() {
  return useQuery({
    queryKey: ['copilot-context'],
    queryFn: async () => {
      try {
        return await client.get('/api/copilot/context');
      } catch (error) {
        console.warn('useCopilotContext: endpoint /api/copilot/context indisponible', error);
        return [];
      }
    },
    staleTime: 30_000,
  })
}

export function useCreateReport() {
  return useMutation({
    mutationFn: async (body: { prompt: string; filters?: any }) => {
      try {
        return await client.post('/api/copilot/reports', body)
      } catch (error) {
        console.warn('useCreateReport: endpoint /api/copilot/reports indisponible', error)
        throw error
      }
    },
  })
}
