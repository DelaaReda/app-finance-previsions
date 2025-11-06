import { useQuery } from '@tanstack/react-query';
import { ensureArray } from '@/lib/safe';

export type StockMeta = {
  ticker: string;
  name?: string;
  sector?: string;
  industry?: string;
  weight?: number;   // optionnel si backend fournit un poids
};

type Resp = { items?: StockMeta[] };

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? '/api';

async function fetchStocksMeta(tickers: string[]): Promise<Resp> {
  const qs = new URLSearchParams();
  if (tickers.length) qs.set('tickers', tickers.join(','));
  const res = await fetch(`${API_BASE}/stocks/meta?${qs.toString()}`, { headers: { 'Accept': 'application/json' }});
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * Retourne les métadonnées des tickers (secteur, industry, weight, …).
 * Affiche Empty state côté UI si l’API n’est pas encore branchée.
 */
export function useStocksMeta(universe: string[]) {
  const uniq = Array.from(new Set(ensureArray(universe).map(t => t.trim()).filter(Boolean)));
  return useQuery({
    queryKey: ['stocks-meta', uniq],
    queryFn: () => fetchStocksMeta(uniq),
    staleTime: 60_000,
    enabled: uniq.length > 0,
  });
}
