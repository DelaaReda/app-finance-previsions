import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export type StocksScreenerHorizon = 'short' | 'medium' | 'long';
export type StocksScreenerSort =
  | 'score'
  | 'risk'
  | 'momentum_30d'
  | 'change_1d'
  | 'mcap'
  | 'pe'
  | 'div_yield'
  | 'quality';

export interface StocksScreenerItem {
  ticker: string;
  name?: string | null;
  sector?: string | null;
  price?: number | null;
  change_1d?: number | null;
  momentum_30d?: number | null;
  score?: number | null;
  risk?: number | null;
  quality?: number | null;
  mcap?: number | null;
  pe?: number | null;
  div_yield?: number | null;
}

export interface StocksScreenerResponse {
  updated_at?: string | null;
  total: number;
  page: number;
  page_size: number;
  items: StocksScreenerItem[];
}

export interface StocksScreenerParams {
  universe?: string[];
  sectors?: string[];
  horizon?: StocksScreenerHorizon;
  q?: string;
  min_mcap?: number;
  max_mcap?: number;
  min_pe?: number;
  max_pe?: number;
  sort?: StocksScreenerSort;
  order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

function buildSearchParams(params: StocksScreenerParams) {
  const searchParams: Record<string, string> = {};
  const universe = ensureArray(params.universe);
  const sectors = ensureArray(params.sectors);

  if (universe.length) searchParams.universe = universe.join(',');
  if (sectors.length) searchParams.sectors = sectors.join(',');
  if (params.horizon) searchParams.horizon = params.horizon;
  if (params.q) searchParams.q = params.q;
  if (params.min_mcap != null) searchParams.min_mcap = String(params.min_mcap);
  if (params.max_mcap != null) searchParams.max_mcap = String(params.max_mcap);
  if (params.min_pe != null) searchParams.min_pe = String(params.min_pe);
  if (params.max_pe != null) searchParams.max_pe = String(params.max_pe);
  if (params.sort) searchParams.sort = params.sort;
  if (params.order) searchParams.order = params.order;
  searchParams.page = String(params.page ?? 1);
  searchParams.page_size = String(params.page_size ?? 25);

  return searchParams;
}

function keyFor(params: StocksScreenerParams) {
  return [
    'stocks-screener',
    ensureArray(params.universe).sort().join(','),
    ensureArray(params.sectors).sort().join(','),
    params.horizon ?? '',
    params.q ?? '',
    params.min_mcap ?? '',
    params.max_mcap ?? '',
    params.min_pe ?? '',
    params.max_pe ?? '',
    params.sort ?? 'score',
    params.order ?? 'desc',
    params.page ?? 1,
    params.page_size ?? 25,
  ] as const;
}

export function useStocksScreener(params: StocksScreenerParams) {
  return useQuery<StocksScreenerResponse>({
    queryKey: keyFor(params),
    keepPreviousData: true,
    queryFn: async () => {
      const searchParams = buildSearchParams(params);
      const json = await api.fetchJson<any>('/stocks/screener', { searchParams });
      return {
        updated_at: json?.updated_at ?? null,
        total: Number(json?.total ?? 0),
        page: Number(json?.page ?? params.page ?? 1),
        page_size: Number(json?.page_size ?? params.page_size ?? 25),
        items: ensureArray<StocksScreenerItem>(json?.items ?? json ?? []),
      };
    },
  });
}
