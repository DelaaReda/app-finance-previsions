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
      const universeResponse = await api.fetchJson<any>('/api/stocks/universe');
      const universeTickers = ensureArray<string>(universeResponse?.tickers ?? universeResponse ?? []);

      const selectedUniverse = ensureArray(params.universe).length
        ? ensureArray(params.universe)
        : universeTickers;

      const sectorFilter = ensureArray(params.sectors);

      // For now sectors are not provided by backend; keep placeholder filtering logic
      let filteredTickers = universeTickers.filter((ticker) => selectedUniverse.includes(ticker));

      if (params.q) {
        const query = params.q.toLowerCase();
        filteredTickers = filteredTickers.filter((ticker) => ticker.toLowerCase().includes(query));
      }

      // If sectors filters are provided but we do not have mapping yet, return empty result to prompt backend integration
      if (sectorFilter.length > 0) {
        filteredTickers = [];
      }

      const total = filteredTickers.length;
      const page = params.page ?? 1;
      const pageSize = params.page_size ?? 25;
      const start = (page - 1) * pageSize;
      const paginatedTickers = filteredTickers.slice(start, start + pageSize);

      const items: StocksScreenerItem[] = paginatedTickers.map((ticker) => ({
        ticker,
        name: ticker,
        sector: null,
        price: null,
        change_1d: null,
        momentum_30d: null,
        score: null,
        risk: null,
        quality: null,
        mcap: null,
        pe: null,
        div_yield: null,
      }));

      return {
        updated_at: universeResponse?.timestamp ?? new Date().toISOString(),
        total,
        page,
        page_size: pageSize,
        items,
      } satisfies StocksScreenerResponse;
    },
  });
}
