import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export type MoversWindow = '1d' | '1w' | '1m' | '3m' | '6m' | '1y';

export interface RawMover {
  ticker: string;
  name?: string | null;
  sector?: string | null;
  industry?: string | null;
  return?: number | null;
  pct_return?: number | null;
  changePct?: number | null;
  price?: number | null;
  volume?: number | null;
}

export interface Mover {
  ticker: string;
  label: string;
  sector?: string | null;
  r: number;
  price?: number | null;
  volume?: number | null;
}

function pickReturn(item: RawMover): number | null {
  const value =
    (typeof item.return === 'number' ? item.return : null) ??
    (typeof item.pct_return === 'number' ? item.pct_return : null) ??
    (typeof item.changePct === 'number' ? item.changePct : null);
  return value === null || Number.isNaN(value) ? null : Number(value);
}

function normalize(item: RawMover): Mover | null {
  const r = pickReturn(item);
  if (r === null) return null;
  const sector = item.sector ? String(item.sector) : '';
  const base = item.name ? String(item.name) : item.ticker;
  const label = sector ? `${base} · ${sector}` : base;
  return {
    ticker: item.ticker,
    label,
    sector: item.sector ?? null,
    r,
    price: item.price ?? null,
    volume: item.volume ?? null,
  };
}

export function useMovers(universe: string[], window: MoversWindow = '1d', limit = 20) {
  const tickers = ensureArray(universe).map((t) => t.trim()).filter(Boolean);
  const joined = tickers.join(',');

  return useQuery({
    queryKey: ['movers', joined, window, limit],
    enabled: tickers.length > 0,
    queryFn: async () => {
      if (!tickers.length) return { top: [] as Mover[], bottom: [] as Mover[] };
      try {
        const json = await api.fetchJson<{ items?: RawMover[] }>('/api/stocks/movers', {
          searchParams: {
            tickers: joined,
            window,
            limit: String(limit),
          },
        });
        const items = ensureArray(json?.items).map(normalize).filter((item): item is Mover => item !== null);

        const sorted = items.slice().sort((a, b) => b.r - a.r);
        const top = sorted.filter((item) => item.r > 0).slice(0, limit);
        const bottom = sorted
          .filter((item) => item.r < 0)
          .sort((a, b) => a.r - b.r)
          .slice(0, limit);

        return { top, bottom };
      } catch (error) {
        console.warn('useMovers: backend endpoint /api/stocks/movers indisponible', error);
        return { top: [], bottom: [] };
      }
    },
    initialData: { top: [] as Mover[], bottom: [] as Mover[] },
    staleTime: 30_000,
  });
}
