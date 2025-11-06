import { useMemo } from 'react';
import { Card, Title, Text } from '@/ui';
import { Alert, Group, Loader } from '@mantine/core';
import { ensureArray, safeFormatNumber } from '@/lib/safe';
import { useStocksMeta } from '@/hooks/useStocksMeta';
import { useForecasts } from '@/hooks/useForecasts';

type Props = {
  universe: string[];
  horizon?: string;
  periods?: string[]; // list of period keys (e.g. ['1d','1w','1m']) used to slice/label columns
  title?: string;
  description?: string;
};

// Simple color scale from red (negative) → white (0) → green (positive)
function scoreToColor(score: number) {
  // clamp -1..1
  const v = Math.max(-1, Math.min(1, score));
  if (!Number.isFinite(v)) return '#eee';
  if (v === 0) return '#fff';
  if (v > 0) {
    // green scale
    const g = Math.round(200 - (1 - v) * 120);
    const r = Math.round(240 - v * 120);
    return `rgb(${r},${g},${r})`;
  }
  // negative → red-ish
  const r = Math.round(200 - (1 + v) * 120);
  const b = Math.round(240 - (-v) * 120);
  return `rgb(${r},${80},${b})`;
}

export function HeatmapWidget({ universe, horizon = '1m', periods = ['1w', '1m', '3m'], title = 'Heatmap secteur × période', description }: Props) {
  const uniq = ensureArray(universe);
  const metaQ = useStocksMeta(uniq);
  const forecastsQ = useForecasts({ horizon: horizon as any, universe: uniq });

  const isLoading = metaQ.isLoading || forecastsQ.isLoading;
  const error = metaQ.error ?? forecastsQ.error;

  if (isLoading) {
    return (
      <Card>
        <Group align="center" justify="center" p="md">
          <Loader size="sm" />
          <Text>Calcul en cours…</Text>
        </Group>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert color="red" title="Erreur">Impossible de charger les données ({String(error)})</Alert>
      </Card>
    );
  }

  const items = ensureArray(forecastsQ.data as any ?? (forecastsQ.data as any)?.items ?? []);
  const metas = ensureArray(metaQ.data?.items ?? []);

  // Build ticker -> sector map
  const tickerToSector = new Map<string, string>();
  for (const m of metas) {
    if (!m?.ticker) continue;
    tickerToSector.set(m.ticker, m.sector ?? 'Unknown');
  }

  // Aggregate scores by sector and period. If forecasts provide 'history' keyed by period use that, else use 'score'
  // For simplicity: periods columns will be labels from `periods` and we compute average per sector
  const aggregation = useMemo(() => {
    const map: Record<string, Record<string, number[]>> = {};
    for (const f of items) {
      const ticker = f.ticker ?? f.symbol;
      if (!ticker) continue;
      const sector = tickerToSector.get(ticker) ?? 'Unknown';
      if (!map[sector]) map[sector] = {};

      // If history exists and is an object keyed by period labels, read them
      const hist = f.history ?? f.history_by_period ?? null;
      if (hist && typeof hist === 'object') {
        for (const p of periods) {
          const val = Number((hist as any)[p]?.score ?? (hist as any)[p]?.value ?? NaN);
          if (!Number.isNaN(val)) {
            map[sector][p] = map[sector][p] ?? [];
            map[sector][p].push(val);
          }
        }
      } else {
        // fallback: use single score for all periods
        const score = Number(f.score ?? f.er ?? NaN);
        if (!Number.isNaN(score)) {
          for (const p of periods) {
            map[sector][p] = map[sector][p] ?? [];
            map[sector][p].push(score);
          }
        }
      }
    }

    // compute averages
    const sectors = Object.keys(map).sort();
    const table: { sector: string; values: Record<string, number> }[] = [];
    for (const s of sectors) {
      const values: Record<string, number> = {};
      for (const p of periods) {
        const arr = map[s][p] ?? [];
        const avg = arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : NaN;
        values[p] = Number.isFinite(avg) ? avg : 0;
      }
      table.push({ sector: s, values });
    }

    return table;
  }, [items, metas, periods, tickerToSector]);

  if (!aggregation.length) {
    return (
      <Card>
        <Title order={4}>{title}</Title>
        {description && <Text c="dimmed" mt="xs">{description}</Text>}
        <Alert mt="md">Aucune donnée disponible pour construire la heatmap.</Alert>
      </Card>
    );
  }

  // Render simple table heatmap
  return (
    <Card>
      <Title order={4}>{title}</Title>
      {description && <Text c="dimmed" mt="xs">{description}</Text>}
      <div className="overflow-auto mt-4">
        <table className="w-full text-sm table-auto border-collapse">
          <thead>
            <tr>
              <th className="text-left p-2">Secteur</th>
              {periods.map(p => (
                <th key={p} className="text-left p-2">{p}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {aggregation.map(row => (
              <tr key={row.sector}>
                <td className="p-2 font-medium">{row.sector}</td>
                {periods.map(p => {
                  const v = row.values[p] ?? 0;
                  const color = scoreToColor(v);
                  return (
                    <td key={p} className="p-1">
                      <div style={{ background: color, padding: '6px 8px', borderRadius: 4 }} title={safeFormatNumber(v, 2)}>
                        <span className="text-xs">{safeFormatNumber(v, 2)}</span>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
