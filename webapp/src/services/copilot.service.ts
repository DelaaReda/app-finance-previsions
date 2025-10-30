/**
 * Service API pour le Pilier 4: LLM COPILOT
 * Q&A, RAG, what-if scenarios
 */

import { apiPost, apiGet } from '@/api/client'
import type { 
  CopilotQuery, 
  CopilotResponse,
  RAGContext,
  WhatIfScenario 
} from '@/types'

export const copilotService = {
  /**
   * Envoie une question au copilot avec RAG
   */
  query: async (query: CopilotQuery): Promise<CopilotResponse> => {
    const result = await apiPost<CopilotResponse>('/copilot/query', query)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Récupère les informations sur le contexte RAG disponible
   */
  getRAGContext: async (): Promise<RAGContext> => {
    const result = await apiGet<RAGContext>('/copilot/rag/context')
    if (!result.ok) throw new Error(result.error)
    return result.data
  },

  /**
   * Crée un scénario what-if
   */
  createScenario: async (scenario: Omit<WhatIfScenario, 'id' | 'created_at'>): Promise<WhatIfScenario> => {
    const result = await apiPost<WhatIfScenario>('/copilot/scenario', scenario)
    if (!result.ok) throw new Error(result.error)
    return result.data
  },
}
