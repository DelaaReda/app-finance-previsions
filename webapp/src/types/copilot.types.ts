// Types pour le pilier Copilot (LLM Q&A + RAG)

import { Source } from './common.types'

export type CopilotMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  sources?: Source[]
  metadata?: {
    tokens?: number
    model?: string
    confidence?: number
  }
}

export type CopilotSession = {
  id: string
  messages: CopilotMessage[]
  context: RAGContext
  createdAt: string
  updatedAt: string
}

export type RAGContext = {
  timeRange: {
    start: string
    end: string
  }
  tickers?: string[]
  topics?: string[]
  dataTypes: ('news' | 'macro' | 'prices' | 'notes')[]
  documentsCount: number
}
export type CopilotQuery = {
  question: string
  context?: RAGContext
  options?: {
    maxSources?: number
    includeCharts?: boolean
    temperature?: number
  }
}

export type CopilotResponse = {
  answer: string
  sources: Source[]
  charts?: ChartData[]
  confidence: number
  limitations?: string[] // Limites explicites de la réponse
  timestamp: string
}

export type ChartData = {
  type: 'line' | 'bar' | 'candlestick'
  title: string
  data: any[] // Format dépend du type de chart
  source: Source
}

export type WhatIfScenario = {
  id: string
  name: string
  description: string
  parameters: Record<string, number>
  results: {
    impact: string
    probability: number
    timeframe: string
  }
  createdAt: string
}
