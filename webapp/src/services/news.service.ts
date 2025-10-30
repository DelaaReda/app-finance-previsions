// Service pour les news (Pilier 3)
import { apiGet, apiPost } from '../api/client'
import type { ApiResponse } from '../types/common'
import type { NewsFeedResponse, NewsItem } from '../types/news'

export async function fetchNews(params: {
  tickers?: string[]
  q?: string
  limit?: number
  window?: string
}): Promise<ApiResponse<NewsFeedResponse>> {
  const queryParts: string[] = []
  
  if (params.tickers) {
    queryParts.push(...params.tickers.map(t => `tickers=${encodeURIComponent(t)}`))
  }
  if (params.q) {
    queryParts.push(`q=${encodeURIComponent(params.q)}`)
  }
  if (params.limit) {
    queryParts.push(`limit=${params.limit}`)
  }
  if (params.window) {
    queryParts.push(`window=${params.window}`)
  }
  
  const query = queryParts.length > 0 ? `?${queryParts.join('&')}` : ''
  return apiGet<NewsFeedResponse>(`/news/feed${query}`)
}

export async function saveNewsToMemory(item: NewsItem): Promise<ApiResponse<{ message: string }>> {
  return apiPost<{ message: string }>('/news/save', item)
}
