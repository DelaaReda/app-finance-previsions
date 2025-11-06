import { keepPreviousData, useQuery, type UseQueryResult } from '@tanstack/react-query';
import { api } from '@/api/client';
import { qk } from '@/lib/keys';
import { adaptNews } from '@/lib/adapters';
import type { NewsArticle } from '@/types/news';

export interface NewsParams {
  universe: string[];
  limit?: number;
  since?: string;
}

function normalizeUniverse(value: string[] | string | undefined): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function normalizeParams(arg1: any, arg2?: any): NewsParams {
  if (Array.isArray(arg1) || arg1 === undefined) {
    return {
      universe: normalizeUniverse(arg1),
      limit: 6,
      since: arg2,
    };
  }
  return {
    universe: normalizeUniverse(arg1?.universe),
    limit: arg1?.limit ?? 6,
    since: arg1?.since,
  };
}

export function useNews(params: NewsParams): UseQueryResult<NewsArticle[]>;
export function useNews(tickers?: string[], since?: string): UseQueryResult<NewsArticle[]>;
export function useNews(arg1?: any, arg2?: any): UseQueryResult<NewsArticle[]> {
  const config = normalizeParams(arg1, arg2);
  const universe = config.universe;
  const limit = config.limit ?? 6;

  return useQuery<NewsArticle[]>({
    queryKey: qk.news(universe, limit),
    enabled: universe.length > 0 || limit > 0,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    queryFn: async () => {
      const data = await api.fetchJson<any>('/api/news/feed', {
        searchParams: {
          tickers: universe.length ? universe.join(',') : undefined,
          limit,
          since: config.since,
        },
      });
      return adaptNews(data);
    },
  });
}
