import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray, asString } from '@/lib/safe';
import { qk } from '@/lib/keys';

type Horizon = 'short' | 'medium' | 'long';

export type { Horizon };

export interface RawMatrixItem {
  ticker: string;
  name?: string | null;
  sector?: string | null;
  themes?: string[] | null;
  short?: number | null;
  medium?: number | null;
  long?: number | null;
  values?: { short?: number | null; medium?: number | null; long?: number | null } | null;
  updated_at?: string | null;
}

export interface MatrixItem {
  ticker: string;
  name: string;
  sector?: string;
  themes: string[];
  values: Record<Horizon, number | undefined>;
  updatedAt?: string | null;
}

function toPct(input?: number | null): number | undefined {
  if (input == null) return undefined;
  const n = Number(input);
  if (!Number.isFinite(n)) return undefined;
  if (Math.abs(n) <= 1) return n * 100;
  return n;
}

function normalizeRow(row: RawMatrixItem): MatrixItem {
  const fallback = row.values ?? {};
  const short = toPct(row.short ?? fallback.short ?? null);
  const medium = toPct(row.medium ?? fallback.medium ?? null);
  const long = toPct(row.long ?? fallback.long ?? null);

  return {
    ticker: asString(row.ticker),
    name: asString(row.name, row.ticker),
    sector: row.sector ?? undefined,
    themes: ensureArray<string>(row.themes ?? []),
    values: { short, medium, long },
    updatedAt: row.updated_at ?? null,
  };
}

export interface PerformanceMatrixParams {
  horizons?: Horizon[];
  tickers?: string[];
  sectors?: string[];
  themes?: string[];
}

const DEFAULT_HORIZONS: Horizon[] = ['short', 'medium', 'long'];

export function usePerformanceMatrix(params: PerformanceMatrixParams) {
  const horizons = params.horizons?.length ? params.horizons : DEFAULT_HORIZONS;
  const tickers = ensureArray(params.tickers);
  const sectors = ensureArray(params.sectors);
  const themes = ensureArray(params.themes);

  return useQuery<MatrixItem[]>({
    queryKey: qk.performanceMatrix(horizons, tickers, sectors, themes),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    queryFn: async () => {
      const searchParams: Record<string, string> = {
        horizons: horizons.join(','),
      };
      if (tickers.length) searchParams.tickers = tickers.join(',');
      if (sectors.length) searchParams.sectors = sectors.join(',');
      if (themes.length) searchParams.themes = themes.join(',');

      try {
        const payload = await api.fetchJson<any>('/api/performance/matrix', { searchParams });
        const items = ensureArray<RawMatrixItem>(payload?.items ?? payload?.data ?? payload);
        return items.map(normalizeRow).filter((row) => row.ticker);
      } catch (error) {
        console.warn('usePerformanceMatrix: endpoint /api/performance/matrix indisponible', error);
        return [];
      }
    },
  });
}
