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

export type NewsFeedResponse = { items: NewsItem[]; next_page?: number } | NewsItem[];

export function normalizeFeed(resp: NewsFeedResponse): { items: NewsItem[]; next_page?: number } {
  return Array.isArray(resp) ? { items: resp, next_page: undefined } : resp;
}
