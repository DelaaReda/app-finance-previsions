/**
 * Custom hooks pour le Copilot LLM
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import { copilotService } from '@/services'
import type { CopilotQuery, CopilotResponse, RAGContext } from '@/types'

/**
 * Hook pour envoyer une query au copilot
 */
export function useCopilotQuery() {
  return useMutation({
    mutationFn: (query: CopilotQuery) => copilotService.query(query),
  })
}

/**
 * Hook pour récupérer le contexte RAG disponible
 */
export function useRAGContext() {
  return useQuery({
    queryKey: ['copilot', 'rag', 'context'],
    queryFn: () => copilotService.getRAGContext(),
    staleTime: 30 * 60 * 1000, // 30 minutes
  })
}
