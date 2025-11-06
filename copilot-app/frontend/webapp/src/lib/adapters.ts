import { ensureArray, asNumber, asString } from '@/lib/safe';
import type { ForecastItem } from '@/types/forecast';
import type { MacroPoint, MacroSeriesMap } from '@/types/macro';
import type { NewsArticle } from '@/types/news';

export function adaptForecasts(payload: any): ForecastItem[] {
  const arr =
    ensureArray(payload?.data?.items) ||
    ensureArray(payload?.data) ||
    ensureArray(payload);

  return arr
    .map((row: any): ForecastItem => ({
      symbol: asString(row?.symbol ?? row?.ticker, ''),
      horizon: (row?.horizon ?? 'short') as any,
      score: asNumber(row?.score ?? row?.signal ?? row?.rank, 0),
      direction: (row?.direction ?? row?.dir ?? 'flat') as any,
      confidence: row?.confidence != null ? asNumber(row?.confidence) : undefined,
      expectedReturn: row?.expected_return != null ? asNumber(row?.expected_return) : undefined,
      updatedAt: asString(row?.updated_at ?? row?.generated_at, undefined as any),
    }))
    .filter((item) => item.symbol);
}

export function adaptMacroSeries(payload: any): MacroSeriesMap {
  const root = payload?.data ?? payload ?? {};
  const result: MacroSeriesMap = {};

  Object.entries(root).forEach(([key, value]) => {
    const points = ensureArray(value).map(
      (point: any): MacroPoint => ({
        date: asString(point?.date ?? point?.t ?? point?.time, ''),
        value: asNumber(point?.value ?? point?.v ?? point?.close ?? point?.x ?? point?.y, 0),
      }),
    );
    result[key] = points.filter((p) => p.date);
  });

  return result;
}

export function adaptNews(payload: any): NewsArticle[] {
  const arr =
    ensureArray(payload?.data?.articles) ||
    ensureArray(payload?.articles) ||
    ensureArray(payload);

  return arr
    .map(
      (article: any): NewsArticle => ({
        id: asString(article?.id, undefined as any),
        title: asString(article?.title, ''),
        url: asString(article?.url ?? article?.link, '#'),
        source: asString(article?.source ?? article?.publisher, undefined as any),
        publishedAt: asString(article?.published_at ?? article?.date ?? article?.timestamp, undefined as any),
        sentiment: (article?.sentiment ?? article?.sent ?? undefined) as any,
        summary: asString(article?.summary ?? article?.snippet ?? article?.description, undefined as any),
        tickers: ensureArray(article?.tickers ?? article?.symbols),
      }),
    )
    .filter((item) => item.title && item.url);
}
