/**
 * Types pour les Market Briefs
 * Daily/Weekly briefs avec Top 3 signaux/risques
 */

// Optional: NewsItem can be imported if needed later
// import { NewsItem } from './news.types'

// Updated to match actual backend response structure
export type MarketBrief = {
  top_signals: any[]      // Top 3
  top_risks: any[]         // Top 3
  picks: any[]              // Tickers with scores > 65
  sources: any[]         // Traçabilité
  generated_at: string       // ISO timestamp
  period: string            // "daily" | "weekly"
  universe: string[]        // Tickers analyzed
  error?: string           // Error message if any
  title?: string           // Optional title
  date?: string           // Optional date
  is_fallback?: boolean
  fallback?: boolean
  fallback_reason?: string
}

export type BriefMacroSnapshot = {
  headline: string
  key_indicators: any[]
  trend: 'bullish' | 'bearish' | 'neutral'
  alert_level: 'normal' | 'warning' | 'critical'
}

export type MarketSnapshot = {
  headline: string
  top_movers: {
    ticker: string
    change_pct: number
    volume_ratio: number
  }[]
  sector_performance: {
    sector: string
    change_pct: number
  }[]
  market_sentiment: 'bullish' | 'bearish' | 'neutral'
}

export type NewsSnapshot = {
  headline: string
  top_stories: any[]
  sentiment_breakdown: {
    positive: number
    negative: number
    neutral: number
  }
  trending_topics: string[]
}

export type BriefExportFormat = 'html' | 'pdf' | 'markdown'

export type BriefFilters = {
  type?: 'daily' | 'weekly' | 'all'
  date_from?: string
  date_to?: string
  tickers?: string[]
}
