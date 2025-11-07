import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import { ensureArray } from '@/lib/safe';

export type StockMeta = {
  ticker: string;
  name?: string;
  sector?: string;
  industry?: string;
  weight?: number;   // optionnel si backend fournit un poids
};

type Resp = { items?: StockMeta[] };

/**
 * Retourne les métadonnées des tickers (secteur, industry, weight, …).
 * Affiche Empty state côté UI si l’API n’est pas encore branchée.
 */
export function useStocksMeta(universe: string[]) {
  const uniq = Array.from(new Set(ensureArray(universe).map(t => t.trim()).filter(Boolean)));
  return useQuery({
    queryKey: ['stocks-meta', uniq],
    placeholderData: keepPreviousData,
    queryFn: async (): Promise<Resp> => {
      if (!uniq.length) return { items: [] };
      const searchParams: Record<string, string> = { tickers: uniq.join(',') };
      const json = await api.fetchJson<any>('/api/stocks/meta', { searchParams });
      const data = json?.data ?? json ?? {};
      return {
        items: ensureArray<StockMeta>(data.items),
      };
    },
    staleTime: 60_000,
    enabled: uniq.length > 0,
  });
}
