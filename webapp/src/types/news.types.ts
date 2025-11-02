// webapp/src/types/news.types.ts
export interface NewsItem {
  symbol?: string
  title?: string
  summary?: string
  url?: string
  published?: string
  source?: string
  score?: number
  news_score_mean?: number
  news_count?: number
  asof?: string
}

export interface NewsFeed {
  rows: NewsItem[]
  count: number
  fallback?: string
}

export interface NewsSentiment {
  sentiment: Record<string, number>
  count: number
}
