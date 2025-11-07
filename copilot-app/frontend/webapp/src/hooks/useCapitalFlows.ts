/**
 * Hook for Capital Flows
 * Fetches capital flows data for SankeyDiagram widget
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export interface FlowNode {
  id: string;
  label: string;
  color?: string;
}

export interface FlowLink {
  source: string;
  target: string;
  value: number;
  color?: string;
}

export interface CapitalFlows {
  nodes: FlowNode[];
  links: FlowLink[];
  lookback_days: number;
  generated_at: string;
}

export function useCapitalFlows() {
  return useQuery({
    queryKey: ['flows', 'capital'],
    queryFn: async () => {
      const response = await apiGet<any>('/api/flows/capital');
      
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as CapitalFlows;
        }
        if ('data' in response) {
          return response.data as CapitalFlows;
        }
        return response as CapitalFlows;
      }
      
      // Fallback empty structure
      return {
        nodes: [],
        links: [],
        lookback_days: 30,
        generated_at: new Date().toISOString(),
      } as CapitalFlows;
    },
    staleTime: 15 * 60 * 1000, // 15 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
    retryDelay: 1000,
  });
}

