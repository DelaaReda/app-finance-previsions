import { useQuery } from '@tanstack/react-query';
import { getNews, NewsArticle } from '@/services/news';
import { ensureArray } from '@/lib/safe';
import { NET } from '@/config/env';

// Make tickers optional to keep existing callers working when no tickers are supplied
export function useNews(tickers: string[] = [], since?: string) {
  const tickersKey = ensureArray(tickers).slice().sort().join(',');
  return useQuery<{ articles: NewsArticle[] }>({
    queryKey: ['news', tickersKey, since || ''],
    queryFn: () => getNews({ tickers, since }),
    staleTime: NET.staleNewsMs,
    gcTime: 10 * 60_000,
    retry: NET.retry,
    select: (payload) => ({ articles: ensureArray(payload.articles) }),
  });
}

