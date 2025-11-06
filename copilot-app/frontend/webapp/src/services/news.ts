import { API_BASE } from '@/config/env';
import { fetchJson } from '@/lib/fetch';
import { ensureArray } from '@/lib/safe';

export interface NewsArticle {
  id: string;
  title: string;
  url: string;
  published_at: string;
  tickers?: string[];
  source?: string;
  sentiment?: 'pos' | 'neu' | 'neg';
}

interface NewsResponse {
  articles: NewsArticle[];
}

export async function getNews(params: { tickers: string[]; since?: string }) {
  const qs = new URLSearchParams({
    tickers: ensureArray(params.tickers).join(','),
  });
  if (params.since) qs.set('since', params.since);
  const data = await fetchJson<unknown>(`${API_BASE}/news?${qs.toString()}`);
  const payload = (data as NewsResponse) || { articles: [] };
  return { articles: ensureArray(payload.articles) };
}

