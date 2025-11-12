import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export type NewsRadarSentiment = number | null | undefined;

export interface NewsRadarArticle {
  id: string;
  title: string;
  url: string;
  source?: string | null;
  tickers: string[];
  themes: string[];
  published_at: string;
  sentiment?: NewsRadarSentiment;
  summary?: string | null;
}

export interface NewsRadarResponse {
  updated_at?: string | null;
  articles: NewsRadarArticle[];
}

export type NewsRadarSort = 'recent' | 'relevance';

export interface NewsRadarParams {
  universe?: string[];
  themes?: string[];
  q?: string;
  from?: string;
  to?: string;
  limit?: number;
  sort?: NewsRadarSort;
}

function buildSearchParams(params: NewsRadarParams): Record<string, string> {
  const searchParams: Record<string, string> = {};
  const universe = ensureArray(params.universe);
  const themes = ensureArray(params.themes);

  if (universe.length) searchParams.tickers = universe.join(',');
  if (themes.length) searchParams.themes = themes.join(',');
  if (params.q) searchParams.q = params.q;
  // Backend doesn't support 'from', 'to', 'sort' - use 'since' instead (e.g. "7d", "1h")
  // Default to 7 days if no time range specified
  searchParams.since = '7d';
  if (params.limit) searchParams.limit = String(params.limit);

  return searchParams;
}

function keyFor(params: NewsRadarParams) {
  const universe = ensureArray(params.universe).sort().join(',');
  const themes = ensureArray(params.themes).sort().join(',');
  return [
    'news-radar',
    universe,
    themes,
    params.q ?? '',
    params.from ?? '',
    params.to ?? '',
    params.limit ?? '',
    params.sort ?? 'recent',
  ] as const;
}

export function useNewsRadar(params: NewsRadarParams) {
  return useQuery<NewsRadarResponse>({
    queryKey: keyFor(params),
    queryFn: async () => {
      const searchParams = buildSearchParams(params);
      const json = await api.fetchJson<any>('/api/news/feed', { searchParams });
      const raw = Array.isArray(json)
        ? json
        : (json?.articles ?? json?.items ?? []);
      const articles = ensureArray(raw).map((article: any) => {
        // Handle both pubDate (ISO string) and timestamp (Unix seconds)
        let publishedAt = article?.pubDate ?? article?.published_at ?? article?.date;
        if (!publishedAt && article?.timestamp) {
          // Convert Unix timestamp (seconds) to ISO string
          publishedAt = new Date(article.timestamp * 1000).toISOString();
        }
        if (!publishedAt) {
          publishedAt = new Date().toISOString();
        }

        return {
          id: String(article?.id ?? article?.url ?? article?.link ?? `${article?.source ?? 'news'}-${article?.title ?? 'item'}`),
          title: String(article?.title ?? 'Sans titre'),
          url: String(article?.link ?? article?.url ?? '#'),
          source: article?.source ?? article?.publisher ?? null,
          tickers: ensureArray(article?.tickers ?? article?.symbols ?? []),
          themes: ensureArray(article?.themes ?? article?.topics ?? []),
          published_at: publishedAt,
          sentiment: typeof article?.sentiment_score === 'number'
            ? article?.sentiment_score
            : typeof article?.sentiment === 'number'
            ? article?.sentiment
            : null,
          summary: article?.summary ?? article?.description ?? null,
        };
      });

      return {
        updated_at: json?.updated_at ?? null,
        articles,
      };
    },
  });
}
