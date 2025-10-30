/**
 * Types pour le Pilier 4: LLM COPILOT
 * Q&A + what-if + RAG avec ≥5 ans de contexte
 */

import { Source } from './common.types'

export type CopilotMessage = {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  sources?: Source[]
  context_used?: ContextReference[]
}

export type ContextReference = {
  type: 'news' | 'price_series' | 'macro_series' | 'document'
  id: string
  title: string
  date: string
  relevance_score: number
  snippet?: string
}

export type CopilotQuery = {
  query: string
  tickers?: string[]
  date_range?: {
    start: string
    end: string
  }
  include_context?: boolean
  max_context_items?: number
}

export type CopilotResponse = {
  answer: string
  sources: Source[]
  context_used: ContextReference[]
  confidence: number
  limitations?: string[]
  timestamp: string
  query_id: string
}

export type RAGContext = {
  news_items: number      // Nombre de news indexées
  price_series: number    // Nombre de séries de prix
  macro_series: number    // Nombre de séries macro
  date_range: {
    start: string
    end: string
  }
  total_documents: number
  last_indexed: string
}

export type WhatIfScenario = {
  id: string
  name: string
  description: string
  parameters: Record<string, number>
  impact_summary: string
  affected_tickers: string[]
  confidence: number
  sources: Source[]
  created_at: string
}
