import { Fragment, useMemo } from 'react';
import { Card, Title, Text, Grid } from '@/ui';
import { BarList, AreaChart } from '@tremor/react';
import { Alert, Loader, Group } from '@mantine/core';
import { ensureArray, nn } from '@/lib/safe';
import { DonutWidget } from '@/components/widgets/DonutWidget';
import { useForecasts } from '@/hooks/useForecasts';

// Types du moteur de template (adapte l'import si ton pack diffère)
import type { DashboardTemplate, TemplateRenderCtx } from './types';

function MomentumLists({ horizon, universe, themes }: { horizon: string; universe: string[]; themes?: string[] }) {
  const { data, isLoading, error } = useForecasts({ horizon: horizon as any, universe, themes });

  if (isLoading) {
    return (
      <Card>
        <Group align="center" justify="center" p="md">
          <Loader size="sm" />
          <Text>Calcul des scores momentum…</Text>
        </Group>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert color="red" title="Erreur">Impossible de récupérer les prévisions ({String(error)})</Alert>
      </Card>
    );
  }

  const items = ensureArray((data as any)?.items ?? (data as any)?.data ?? data);
  // On utilise "score" (ou "er" si présent) comme proxy momentum
  const withScore = items
    .map((it: any) => ({
      name: it.ticker ?? it.symbol ?? 'N/A',
      score: typeof it.score === 'number' ? it.score : (typeof it.er === 'number' ? it.er : 0),
    }))
    .filter((x: any) => Number.isFinite(x.score));

  const top = [...withScore].sort((a, b) => b.score - a.score).slice(0, 10);
  const flop = [...withScore].sort((a, b) => a.score - b.score).slice(0, 10);

  if (withScore.length === 0) {
    return (
      <Card>
        <Title order={4}>Momentum — Top / Flop</Title>
        <Alert mt="md">Aucun score exploitable pour l’univers/horizon sélectionné.</Alert>
      </Card>
    );
  }

  return (
    <Grid>
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Card>
          <Title order={4}>Top 10 (score)</Title>
          <BarList
            data={top.map(t => ({ name: t.name, value: Number(t.score.toFixed(2)) }))}
            className="mt-4"
          />
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 6 }}>
        <Card>
          <Title order={4}>Flop 10 (score)</Title>
          <BarList
            data={flop.map(t => ({ name: t.name, value: Number(t.score.toFixed(2)) }))}
            className="mt-4"
          />
        </Card>
      </Grid.Col>
    </Grid>
  );
}

function MomentumSparkline({ horizon, universe, themes }: { horizon: string; universe: string[]; themes?: string[] }) {
  const { data, isLoading, error } = useForecasts({ horizon: horizon as any, universe, themes });

  if (isLoading) {
    return (
      <Card>
        <Group align="center" justify="center" p="md">
          <Loader size="sm" />
          <Text>Chargement…</Text>
        </Group>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Alert color="red" title="Erreur">Impossible de récupérer les prévisions ({String(error)})</Alert>
      </Card>
    );
  }

  const items = ensureArray((data as any)?.items ?? (data as any)?.data ?? data);
  // Fabrique un petit dataset time-series par ticker si "history" est dispo; sinon fallback à score-only
  const chart = useMemo(() => {
    // format attendu par AreaChart: [{ time: '2025-11-03', AAPL: 0.12, MSFT: 0.08, … }, …]
    // Si pas d'historique, on mappe un seul point synthétique
    const byTicker: Record<string, number[]> = {};
    let times: string[] = [];

    for (const it of items) {
      const tk = it.ticker ?? it.symbol;
      if (!tk) continue;
      const hist = ensureArray(it.history);
      if (hist.length > 0) {
        // suppose hist = [{ t: '2025-11-01', score: 0.1 }, …]
        times = hist.map((h: any) => String(h.t ?? h.time ?? h.date));
        byTicker[tk] = hist.map((h: any) => Number(h.score ?? h.er ?? 0));
      } else {
        times = ['now']; // fallback
        byTicker[tk] = [Number(it.score ?? it.er ?? 0)];
      }
    }

    const rows = times.map((t, idx) => {
      const row: any = { time: t };
      for (const tk of Object.keys(byTicker)) row[tk] = byTicker[tk]?.[idx] ?? null;
      return row;
    });

    return rows;
  }, [items]);

  if (chart.length === 0) {
    return (
      <Card>
        <Title order={4}>Momentum — courbes</Title>
        <Alert mt="md">Aucune série exploitable.</Alert>
      </Card>
    );
  }

  const keys = Object.keys(chart[0]).filter(k => k !== 'time').slice(0, 6); // limiter l’encombrement

  return (
    <Card>
      <Title order={4}>Momentum — courbes {keys.length > 0 ? `(top ${keys.length})` : ''}</Title>
      <AreaChart
        data={chart}
        index="time"
        categories={keys}
        valueFormatter={(v: number) => (Number.isFinite(v) ? v.toFixed(2) : '—')}
        showLegend
        yAxisWidth={48}
        className="mt-4"
      />
    </Card>
  );
}

export function StocksMomentumTemplate({ horizon, universe, themes }: TemplateRenderCtx) {
  // horizon is often a string like '1d' or '1m' — nn() coerces to number so avoid passing string fallback
  const hz = typeof horizon === 'string' ? horizon : (horizon == null ? '1m' : String(nn(horizon)));
  const uni = ensureArray(universe).length ? ensureArray(universe) : ['SPY','QQQ','AAPL','MSFT','NVDA','META','GOOGL','AMZN'];

  return (
    <Fragment>
      <Grid>
        <Grid.Col span={{ base: 12, md: 4 }}>
          <DonutWidget
            universe={uni}
            title="Répartition sectorielle"
            description="Vue secteurs basée sur les tickers sélectionnés"
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <MomentumSparkline horizon={hz} universe={uni} themes={themes} />
        </Grid.Col>
      </Grid>

      <div className="mt-6">
        <MomentumLists horizon={hz} universe={uni} themes={themes} />
      </div>
    </Fragment>
  );
}

export const stocksMomentumTemplate: DashboardTemplate = {
  slug: 'stocks-momentum',
  label: 'Stocks Momentum',
  description: 'Répartition sectorielle + tops/flops et courbes momentum',
  render: (ctx: TemplateRenderCtx) => <StocksMomentumTemplate {...ctx} />,
};
