// Types pour les news (Pilier 3)
export interface NewsItem {
  title: string
  url: string
  published: string
  source: string
  summary: string
  score: number
  importance: number
  freshness: number
  relevance: number
  sentiment: string | null
  entities: string[]
  tickers: string[]
}

export interface NewsFeedResponse {
  items: NewsItem[]
  count: number
  generated_at: string
}
