// webapp/src/services/copilot.service.ts
import { apiGet, apiPost } from '../api/client'
import type { CopilotAskRequest, CopilotResponse, CopilotHistory } from '../types/copilot.types'

export const copilotService = {
  /**
   * Ask LLM with RAG (5 years context)
   */
  ask: async (request: CopilotAskRequest) => {
    return apiPost<CopilotResponse>('/api/copilot/ask', request)
  },

  /**
   * Get conversation history
   */
  getHistory: async (limit = 20) => {
    return apiGet<CopilotHistory>('/api/copilot/history', { limit: String(limit) })
  },
  
  /**
   * Get RAG store statistics
   */
  getRAGStats: async () => {
    return apiGet<any>('/api/rag/stats')
  },
  
  /**
   * Create a new conversation session
   */
  createSession: async () => {
    return apiPost<any>('/api/copilot/session', {})
  }
}
