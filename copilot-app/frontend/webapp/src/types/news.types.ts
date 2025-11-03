// webapp/src/types/news.types.ts
export interface NewsItem {
  id: string;
  ticker?: string;
  title: string;
  text?: string;
  url: string;
  source: string;
  published_at: string; // ISO
  sentiment?: number;   // -1..+1 éventuel
}

export type NewsFeedBackendResponse = {
  articles: NewsItem[];
  count: number;
  total: number;
  filters: {
    tickers?: string[];
    since?: string;
    score_min?: number;
    region?: string;
  };
  trace: {
    created_at: string;
    source: string;
    asof_date: string;
    hash: string;
  };
};

export type NewsFeedResponse = { items: NewsItem[]; next_page?: number } | NewsItem[];

export function normalizeFeed(resp: NewsFeedResponse | NewsFeedBackendResponse): { items: NewsItem[]; next_page?: number } {
  // Handle the new backend response structure (with articles, count, total, filters, trace)
  if ('articles' in resp) {
    const backendResp = resp as NewsFeedBackendResponse;
    return { items: backendResp.articles, next_page: undefined };
  }
  // Handle the original expected structures
  return Array.isArray(resp) ? { items: resp, next_page: undefined } : resp;
}
