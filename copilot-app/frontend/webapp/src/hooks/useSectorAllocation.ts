/**
 * Hook for Sector Allocation
 * Fetches sector allocation data for SectorWheel and TreemapChart widgets
 */

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';

export interface SectorData {
  id: string;
  label: string;
  value: number; // Percentage
  weight: number;
  tickers: string[];
  count: number;
  color?: string;
}

export interface SectorAllocation {
  sectors: SectorData[];
  total_tickers: number;
  total_sectors: number;
  generated_at: string;
}

export function useSectorAllocation() {
  return useQuery({
    queryKey: ['stocks', 'sectors'],
    queryFn: async () => {
      const response = await apiGet<any>('/api/stocks/sectors');
      
      if (response && typeof response === 'object') {
        if ('ok' in response && response.ok && 'data' in response) {
          return response.data as SectorAllocation;
        }
        if ('data' in response) {
          return response.data as SectorAllocation;
        }
        return response as SectorAllocation;
      }
      
      // Fallback empty structure
      return {
        sectors: [],
        total_tickers: 0,
        total_sectors: 0,
        generated_at: new Date().toISOString(),
      } as SectorAllocation;
    },
    staleTime: 15 * 60 * 1000, // 15 minutes - secteurs changent rarement
    cacheTime: 30 * 60 * 1000, // 30 minutes
    retry: 2,
    retryDelay: 1000,
    refetchOnWindowFocus: false, // Éviter refetch automatique
    refetchOnMount: false, // Ne pas refetch si déjà en cache
  });
}

