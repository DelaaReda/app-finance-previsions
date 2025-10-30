// Service pour le pilier Actions

import { apiGet, apiPost } from './api'
import { Stock, StockAnalysis, TechnicalIndicators, Watchlist } from '@/types/stocks.types'
import type { ApiResult } from './api'

export const stocksService = {
  // Recherche d'actions
  search: async (query: string): Promise<ApiResult<Stock[]>> => {
    return apiGet<Stock[]>('/stocks/search', { q: query })
  },

  // Info d'une action
  getStock: async (ticker: string): Promise<ApiResult<Stock>> => {
    return apiGet<Stock>(`/stocks/${ticker}`)
  },

  // Analyse complète (prix + indicateurs + score + signaux)
  getAnalysis: async (ticker: string): Promise<ApiResult<StockAnalysis>> => {
    return apiGet<StockAnalysis>(`/stocks/${ticker}/analysis`)
  },

  // Indicateurs techniques
  getTechnicals: async (ticker: string): Promise<ApiResult<TechnicalIndicators>> => {
    return apiGet<TechnicalIndicators>(`/stocks/${ticker}/technicals`)
  },

  // Historique de prix
  getPriceHistory: async (
    ticker: string, 
    period: string = '1y'
  ): Promise<ApiResult<any>> => {
    return apiGet(`/stocks/${ticker}/history`, { period })
  },
  // Watchlists
  getWatchlists: async (): Promise<ApiResult<Watchlist[]>> => {
    return apiGet<Watchlist[]>('/stocks/watchlists')
  },

  createWatchlist: async (name: string, tickers: string[]): Promise<ApiResult<Watchlist>> => {
    return apiPost<Watchlist>('/stocks/watchlists', { name, tickers })
  },

  addToWatchlist: async (watchlistId: string, ticker: string): Promise<ApiResult<void>> => {
    return apiPost<void>(`/stocks/watchlists/${watchlistId}/add`, { ticker })
  },

  // Comparaison secteur
  getSectorComparison: async (sector: string): Promise<ApiResult<any>> => {
    return apiGet(`/stocks/sector/${sector}/comparison`)
  }
}
