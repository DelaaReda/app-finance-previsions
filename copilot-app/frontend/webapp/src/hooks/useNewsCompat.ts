import { useMemo, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { api } from '@/api/client';

// Map sentiment categories to a numeric score for legacy UIs
function mapSentimentToScore(s: unknown) {
  if (s === 'pos') return 0.7;
  if (s === 'neg') return -0.7;
  return 0;
}

/**
 * Compatibility wrapper for legacy consumers that expect the older
 * shape: { items, filters, setFilters, loading, error, hasMore, loadMore, freshness }
 * Now with real pagination support (Sprint 4 - Tâche 4.1)
 */
export function useNewsCompat(tickers: string[] = []) {
  const [page, setPage] = useState(1);
  const [filters, setFiltersState] = useState({
    tickers: (tickers || []).join(','),
    since: '7d' as string,
    region: 'all' as string,
    score_min: 0 as number,
    q: '' as string,
  });

  // Fetch all pages up to current page using useQueries
  const pagesToFetch = Array.from({ length: page }, (_, i) => i + 1);
  
  const queries = useQueries({
    queries: pagesToFetch.map((p) => ({
      queryKey: ['news-feed', filters, p],
      queryFn: async () => {
        const searchParams: Record<string, string> = {
          limit: '50',
          page: String(p),
          since: filters.since || '7d',
          sentiment_min: String(filters.score_min || -1.0),
          sentiment_max: '1.0',
        };
        
        if (filters.tickers) {
          searchParams.tickers = filters.tickers;
        }
        if (filters.q) {
          searchParams.q = filters.q;
        }
        
        const json = await api.fetchJson<any>('/api/news/feed', { searchParams });
        return json?.data || json;
      },
      staleTime: 30_000, // 30 seconds
      keepPreviousData: true,
    })),
  });

  // Combine all pages
  const allData = queries.map((q) => q.data).filter(Boolean);
  const currentPageData = queries[queries.length - 1]?.data;
  const isLoading = queries.some((q) => q.isLoading);
  const isFetching = queries.some((q) => q.isFetching);
  const error = queries.find((q) => q.error)?.error;

  // Accumulate articles from all pages
  const raw = allData.flatMap((d) => d?.articles || []);
  const hasMore = currentPageData?.has_more || false;

  const items = raw.map((a: any) => ({
    id: a.id || a.url || a.link,
    title: a.title || 'Sans titre',
    description: a.description ?? a.summary ?? '',
    link: a.url ?? a.link ?? '#',
    pubDate: a.pubDate ?? a.published_at ?? a.timestamp,
    timestamp: a.pubDate ?? a.published_at ?? a.timestamp,
    sentiment_score: typeof a.sentiment === 'string' ? mapSentimentToScore(a.sentiment) : (a.sentiment_score ?? 0),
    tickers: a.tickers ?? a.tickerSymbols ?? [],
    source: a.source ?? a.source_name ?? 'Unknown',
  }));

  const loading = isLoading || isFetching;
  const freshness = currentPageData?.freshness || currentPageData?.last_update || allData[0]?.freshness || allData[0]?.last_update || null;

  const setFilters = (newFilters: any) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
    setPage(1); // Reset to first page when filters change
  };

  const loadMore = () => {
    if (hasMore && !loading) {
      setPage((prev) => prev + 1);
    }
  };

  return useMemo(
    () => ({ items, filters, setFilters, loading, error, hasMore, loadMore, freshness }),
    [items, filters, loading, error, hasMore, freshness],
  );
}
