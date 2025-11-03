// webapp/src/hooks/useNews.ts
import { useEffect, useState, useCallback } from "react";
import { normalizeFeed, NewsItem } from "@/types/news.types";
import { getNewsFeed } from "@/services/news.service";

export interface NewsFilters {
  tickers?: string; since?: string; region?: string; score_min?: number;
}

export function useNews(initial: NewsFilters = {}) {
  const [filters, setFilters] = useState<NewsFilters>({
    since: "7d",
    region: "all",
    score_min: 0.0,
    ...initial
  });
  const [page, setPage] = useState<number>(1);
  const [items, setItems] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);

  const fetchPage = useCallback(async (reset: boolean) => {
    setLoading(true); setError(null);
    try {
      // Convert tickers from comma-separated string to array if it exists
      const tickersArray = filters.tickers ? filters.tickers.split(',').map(t => t.trim()) : undefined;
      
      const params = {
        tickers: tickersArray,
        since: filters.since || "7d",
        region: filters.region || "all",
        score_min: filters.score_min !== undefined ? filters.score_min : 0.0,
        limit: 50
      };
      
      const resp = await getNewsFeed(params);
      if (!resp.ok) {
        throw new Error(resp.error || "Erreur de chargement des actualités");
      }
      
      // The response data contains the backend response with articles, count, etc.
      const backendResponse = resp?.data;
      
      // Handle the backend response structure properly
      if (backendResponse && typeof backendResponse === 'object' && 'articles' in backendResponse) {
        // This is the new backend response format with wrapper
        const payload = backendResponse as any;
        const { items: chunk, next_page } = normalizeFeed(payload);
        
        // Calculate if there are more articles to load
        // If we got back less than limit, or if count < total, there might be no more
        // For now, use a simple heuristic based on chunk size and backend total
        setItems(prev => reset ? chunk : [...prev, ...chunk]);
        
        // Determine if there are more items to load based on the response
        // If we have fewer items than the limit, we're probably at the end
        // If total is known and we already have that many, no more
        const backendResp = backendResponse as { articles: NewsItem[], count?: number, total?: number };
        let moreAvailable = chunk.length === 50; // If we got exactly 50, there might be more
        
        if (typeof backendResp.total === 'number') {
          // If we have more items than total, we're definitely done
          const currentTotal = reset ? chunk.length : items.length + chunk.length;
          moreAvailable = currentTotal < backendResp.total;
        }
        
        setHasMore(moreAvailable);
      } else {
        // Fallback to old format if needed
        const payload = backendResponse ?? ([] as any);
        const { items: chunk, next_page } = normalizeFeed(payload);
        setItems(prev => reset ? chunk : [...prev, ...chunk]);
        setHasMore(Boolean(next_page) || (chunk.length === 50));
      }
    } catch (e: any) {
      setError(e.message ?? "Erreur");
    } finally {
      setLoading(false);
    }
  }, [filters, items.length]);

  useEffect(() => { setPage(1); fetchPage(true); }, [filters, fetchPage]);
  useEffect(() => { if (page > 1) fetchPage(false); }, [page, fetchPage]);

  return { items, filters, setFilters, loading, error, hasMore, loadMore: () => setPage(p => p + 1) };
}
