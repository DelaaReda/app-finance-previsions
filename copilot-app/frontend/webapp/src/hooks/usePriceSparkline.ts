import { useEffect, useState } from 'react';
import { apiGet } from '@/api/client';
import type { StockPriceData } from '@/types/stocks.types';

type Options = {
  enabled?: boolean;
  limit?: number; // max number of points to return (slice from end)
  interval?: string; // e.g., '1d'
  downsample?: number; // server-side downsample hint
};

export function usePriceSparkline(
  ticker: string | undefined,
  { enabled = true, limit = 60, interval = '1d', downsample = 400 }: Options = {},
) {
  const [values, setValues] = useState<number[] | null>(null);
  const [isLoading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!enabled || !ticker) return;
      setLoading(true);
      setError(null);
      try {
        const resp = await apiGet<StockPriceData>('/api/stocks/prices', {
          ticker,
          interval,
          downsample: String(downsample),
        });
        if (!cancelled) {
          if (resp.ok && resp.data) {
            const pts = Array.isArray(resp.data.points) ? resp.data.points : [];
            const vals = pts.map((p) => p?.value).filter((v): v is number => typeof v === 'number');
            setValues(limit > 0 ? vals.slice(-limit) : vals);
          } else {
            setError(resp.error ?? 'Erreur de chargement');
          }
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message ?? String(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [ticker, enabled, limit, interval, downsample]);

  return { values, isLoading, error };
}

