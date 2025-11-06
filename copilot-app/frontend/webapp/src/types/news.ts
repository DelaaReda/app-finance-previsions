export interface NewsArticle {
  id?: string;
  title: string;
  url: string;
  source?: string;
  publishedAt?: string;
  sentiment?: 'pos' | 'neg' | 'neu';
  summary?: string;
  tickers?: string[];
}
