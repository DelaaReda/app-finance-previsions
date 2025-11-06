import { useQuery } from '@tanstack/react-query';
import { getNews, NewsArticle } from '@/services/news';
import { ensureArray } from '@/lib/safe';
import { NET } from '@/config/env';

export function useNews(tickers: string[], since?: string) {
  return useQuery<{ articles: NewsArticle[] }>({
    queryKey: ['news', ensureArray(tickers).sort().join(','), since || ''],
    queryFn: () => getNews({ tickers, since }),
    staleTime: NET.staleNewsMs,
    gcTime: 10 * 60_000,
    retry: NET.retry,
    select: (payload) => ({ articles: ensureArray(payload.articles) }),
  });
}

