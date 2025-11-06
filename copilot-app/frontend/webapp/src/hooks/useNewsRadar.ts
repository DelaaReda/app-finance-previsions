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

  if (universe.length) searchParams.universe = universe.join(',');
  if (themes.length) searchParams.themes = themes.join(',');
  if (params.q) searchParams.q = params.q;
  if (params.from) searchParams.from = params.from;
  if (params.to) searchParams.to = params.to;
  if (params.limit) searchParams.limit = String(params.limit);
  if (params.sort) searchParams.sort = params.sort;

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
      const json = await api.fetchJson<any>('/news', { searchParams });
      const articles = ensureArray(json?.articles ?? json).map((article: any) => ({
        id: String(article?.id ?? article?.url ?? `${article?.source ?? 'news'}-${article?.title ?? 'item'}`),
        title: String(article?.title ?? 'Sans titre'),
        url: String(article?.url ?? '#'),
        source: article?.source ?? article?.publisher ?? null,
        tickers: ensureArray(article?.tickers ?? article?.symbols ?? []),
        themes: ensureArray(article?.themes ?? article?.topics ?? []),
        published_at: String(article?.published_at ?? article?.date ?? article?.timestamp ?? new Date().toISOString()),
        sentiment: typeof article?.sentiment_score === 'number'
          ? article?.sentiment_score
          : typeof article?.sentiment === 'number'
          ? article?.sentiment
          : null,
        summary: article?.summary ?? article?.description ?? null,
      }));

      return {
        updated_at: json?.updated_at ?? null,
        articles,
      };
    },
  });
}
