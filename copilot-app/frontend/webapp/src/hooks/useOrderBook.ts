/**
 * Hook for OrderBook
 * Fetches orderbook data (bids/asks) for OrderBook widget
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export interface OrderBookLevel {
  price: number;
  quantity: number;
}

export interface OrderBook {
  ticker: string;
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  lastPrice: number;
  spread: number;
  spreadPct: number;
  timestamp: string;
}

export function useOrderBook(ticker: string, enabled: boolean = true) {
  return useQuery({
    queryKey: ['orderbook', ticker],
    queryFn: async () => {
      if (!ticker) {
        throw new Error('Ticker is required');
      }
      
      const response = await apiGet<any>('/api/orderbook', { ticker });
      
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as OrderBook;
        }
        if ('data' in response) {
          return response.data as OrderBook;
        }
        return response as OrderBook;
      }
      
      // Fallback empty structure
      return {
        ticker: ticker.toUpperCase(),
        bids: [],
        asks: [],
        lastPrice: 0,
        spread: 0,
        spreadPct: 0,
        timestamp: new Date().toISOString(),
      } as OrderBook;
    },
    enabled: enabled && !!ticker,
    staleTime: 30 * 1000, // 30 seconds (orderbook changes frequently)
    cacheTime: 2 * 60 * 1000, // 2 minutes
    retry: 1,
    retryDelay: 500,
    refetchInterval: 10 * 1000, // Refetch every 10 seconds for real-time feel
    refetchOnWindowFocus: false, // Éviter refetch automatique (déjà géré par refetchInterval)
  });
}

