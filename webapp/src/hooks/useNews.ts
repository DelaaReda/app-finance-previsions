// webapp/src/hooks/useNews.ts
import { useEffect, useState, useCallback } from "react";
import { normalizeFeed, NewsItem } from "@/types/news.types";
import { getNewsFeed } from "@/services/news.service";

export interface NewsFilters {
  ticker?: string; q?: string; start?: string; end?: string;
}

export function useNews(initial: NewsFilters = {}) {
  const [filters, setFilters] = useState<NewsFilters>(initial);
  const [page, setPage] = useState<number>(1);
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const fetchPage = useCallback(async (reset: boolean) => {
    setLoading(true); setError(null);
    try {
      const resp = await getNewsFeed({ ...filters, page, limit: 50 });
      const { items: chunk, next_page } = normalizeFeed(resp);
      setItems(prev => reset ? chunk : [...prev, ...chunk]);
      setHasMore(Boolean(next_page) || (chunk.length === 50));
    } catch (e: any) {
      setError(e.message ?? "Erreur");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => { setPage(1); fetchPage(true); }, [filters, fetchPage]);
  useEffect(() => { if (page > 1) fetchPage(false); }, [page, fetchPage]);

  return { items, filters, setFilters, loading, error, hasMore, loadMore: () => setPage(p => p + 1) };
}
