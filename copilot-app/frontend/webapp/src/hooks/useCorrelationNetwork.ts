/**
 * Hook for Correlation Network
 * Fetches correlation matrix and network data for CorrelationNetwork and CorrelationHeatmap widgets
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export interface CorrelationNode {
  id: string;
  label: string;
  sector?: string;
  index?: number;
}

export interface CorrelationLink {
  source: string;
  target: string;
  correlation: number;
  strength?: number;
}

export interface CorrelationMatrix {
  matrix: Record<string, Record<string, number>>;
  tickers: string[];
  lookback_days: number;
  generated_at: string;
}

export interface CorrelationNetwork {
  nodes: CorrelationNode[];
  links: CorrelationLink[];
  threshold: number;
  generated_at: string;
}

export function useCorrelationMatrix() {
  return useQuery({
    queryKey: ['correlations', 'matrix'],
    queryFn: async () => {
      const response = await apiGet<any>('/api/correlations/matrix');
      
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as CorrelationMatrix;
        }
        if ('data' in response) {
          return response.data as CorrelationMatrix;
        }
        return response as CorrelationMatrix;
      }
      
      // Fallback empty structure
      return {
        matrix: {},
        tickers: [],
        lookback_days: 90,
        generated_at: new Date().toISOString(),
      } as CorrelationMatrix;
    },
    staleTime: 15 * 60 * 1000, // 15 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
    retryDelay: 1000,
  });
}

export function useCorrelationNetwork(threshold: number = 0.5) {
  return useQuery({
    queryKey: ['correlations', 'network', threshold],
    queryFn: async () => {
      const response = await apiGet<any>('/api/correlations/network', { threshold });
      
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as CorrelationNetwork;
        }
        if ('data' in response) {
          return response.data as CorrelationNetwork;
        }
        return response as CorrelationNetwork;
      }
      
      // Fallback empty structure
      return {
        nodes: [],
        links: [],
        threshold,
        generated_at: new Date().toISOString(),
      } as CorrelationNetwork;
    },
    staleTime: 15 * 60 * 1000, // 15 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
    retryDelay: 1000,
  });
}

