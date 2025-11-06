import { useMemo } from 'react';
import { useNews } from '@/hooks/useNews';

// Map sentiment categories to a numeric score for legacy UIs
function mapSentimentToScore(s: unknown) {
  if (s === 'pos') return 0.7;
  if (s === 'neg') return -0.7;
  return 0;
}

/**
 * Compatibility wrapper for legacy consumers that expect the older
 * shape: { items, filters, setFilters, loading, error, hasMore, loadMore, freshness }
 * It delegates to `useNews` and maps the shape conservatively.
 */
export function useNewsCompat(tickers: string[] = []) {
  const q = useNews({ universe: tickers, limit: 12 });

  const raw = q.data ?? [];

  const items = raw.map((a: any) => ({
    id: a.id,
    title: a.title,
    description: a.description ?? a.summary ?? '',
    link: a.url ?? a.link,
    pubDate: a.publishedAt ?? a.pubDate ?? a.timestamp,
    timestamp: a.publishedAt ?? a.timestamp,
    sentiment_score: typeof a.sentiment === 'string' ? mapSentimentToScore(a.sentiment) : (a.sentiment_score ?? 0),
    tickers: a.tickers ?? a.tickerSymbols ?? [],
    source: a.source,
  }));

  const loading = q.isLoading || q.isFetching;
  const error = q.error as any;

  // Minimal filters surface
  const filters = { tickers: (tickers || []).join(','), since: undefined, region: undefined, score_min: undefined } as any;
  const setFilters = (_: any) => {
    // no-op compatibility shim; prefer consumers to migrate to new hook signature
    return;
  };

  const hasMore = false;
  const loadMore = () => Promise.resolve();
  const freshness = raw[0]?.publishedAt ?? null;

  return useMemo(
    () => ({ items, filters, setFilters, loading, error, hasMore, loadMore, freshness }),
    [items, loading, error, hasMore, freshness],
  );
}
