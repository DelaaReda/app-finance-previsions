import { ensureArray, asNumber, asString } from '@/lib/safe';
import type { ForecastItem, ForecastSparkPoint } from '@/types/forecast';
import type { MacroPoint, MacroSeriesMap } from '@/types/macro';
import type { NewsArticle } from '@/types/news';

export function adaptForecasts(payload: any): ForecastItem[] {
  const arr = ensureArray(payload?.items) || ensureArray(payload?.data?.items) || ensureArray(payload?.data) || ensureArray(payload);

  return arr
    .map((row: any): ForecastItem | null => {
      const ticker = asString(row?.ticker ?? row?.symbol ?? row?.id, '');
      if (!ticker) return null;

      const score = asNumber(row?.score ?? row?.signal ?? row?.rank, 0);
      const direction = (row?.direction ?? row?.dir ?? 'neutral') as ForecastItem['direction'];
      let confidenceRaw = row?.confidence != null ? asNumber(row?.confidence, 0) : 0;
      if (Number.isFinite(confidenceRaw) && confidenceRaw > 1) {
        confidenceRaw = confidenceRaw / 100;
      }

      let expectedRaw = row?.expected_return_pct != null ? asNumber(row?.expected_return_pct, null as any) : row?.expected_return != null ? asNumber(row?.expected_return, null as any) : null;
      if (expectedRaw != null && Math.abs(expectedRaw) <= 1) {
        expectedRaw = expectedRaw * 100;
      }

      const sparkline: ForecastSparkPoint[] | undefined = ensureArray(row?.sparkline).length
        ? ensureArray(row?.sparkline).map((point: any) => ({
            date: asString(point?.date ?? point?.t ?? point?.time, ''),
            value: point?.value != null ? asNumber(point?.value) : point?.v != null ? asNumber(point?.v) : null,
          })).filter((point) => point.date)
        : undefined;

      const forecastedAt = asString(row?.forecasted_at ?? row?.updated_at ?? row?.generated_at, undefined as any);
      const components = row?.components && typeof row?.components === 'object' ? row.components : undefined;
      const themes = ensureArray(row?.themes).map((theme) => asString(theme, '')).filter(Boolean);

      return {
        ticker,
        symbol: ticker,
        name: row?.name ?? row?.company ?? null,
        sector: row?.sector ?? null,
        horizon: (row?.horizon ?? 'short') as any,
        themes,
        score,
        direction,
        confidence: confidenceRaw,
        confidence_pct: confidenceRaw != null ? confidenceRaw * 100 : null,
        expected_return_pct: expectedRaw,
        expectedReturnPct: expectedRaw,
        expectedReturn: expectedRaw != null ? expectedRaw / 100 : null,
        forecasted_at: forecastedAt,
        forecastedAt,
        model_version: row?.model_version ?? row?.model ?? row?.model_name ?? null,
        components,
        sparkline,
        explain: row?.explain ?? row?.explanation ?? undefined,
        updatedAt: forecastedAt,
      } satisfies ForecastItem;
    })
    .filter((item): item is ForecastItem => Boolean(item?.ticker));
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
