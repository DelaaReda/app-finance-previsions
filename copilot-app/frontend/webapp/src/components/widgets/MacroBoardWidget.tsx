import { useMemo, useState } from 'react';
import { AreaChart, LineChart, BarChart } from '@tremor/react';
import {
  Alert,
  Divider,
  Group,
  MultiSelect,
  Select,
  SegmentedControl,
  Stack,
  Switch,
  Tooltip,
} from '@mantine/core';
import { IconDownload, IconRefresh } from '@tabler/icons-react';
import { Card, Title, Button, Text } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import { ensureArray } from '@/lib/safe';
import { useMacroSeries, type MacroSeries, type MacroPoint, type MacroFreq } from '@/hooks/useMacro';

type Horizon = '1Y' | '3Y' | '5Y' | 'MAX';

function sliceByHorizon(points: MacroPoint[], horizon: Horizon): MacroPoint[] {
  if (!points.length || horizon === 'MAX') return points;
  const end = new Date(points[points.length - 1].date).getTime();
  const days = horizon === '1Y' ? 365 : horizon === '3Y' ? 3 * 365 : 5 * 365;
  const start = end - days * 24 * 3600 * 1000;
  return points.filter((point) => new Date(point.date).getTime() >= start);
}

function normalizeBase100(points: MacroPoint[]): MacroPoint[] {
  const valid = points.filter((p) => typeof p.value === 'number');
  if (!valid.length) return points;
  const base = valid[0].value!;
  if (base === 0) return points;
  return points.map((p) => ({
    date: p.date,
    value: p.value == null ? null : (p.value / base) * 100,
  }));
}

function percentChange(curr: number | null | undefined, prev: number | null | undefined) {
  if (curr == null || prev == null || prev === 0) return null;
  return ((curr - prev) / Math.abs(prev)) * 100;
}

function monthOverMonth(series: MacroSeries): MacroPoint[] {
  const pts = ensureArray(series.points);
  return pts.map((point, index) => ({
    date: point.date,
    value: percentChange(point.value, index > 0 ? pts[index - 1].value : null),
  }));
}

function yearOverYear(series: MacroSeries): MacroPoint[] {
  const pts = ensureArray(series.points);
  return pts.map((point, index) => ({
    date: point.date,
    value: percentChange(point.value, index >= 12 ? pts[index - 12].value : null),
  }));
}

function exportCsv(series: MacroSeries[], options: { horizon: Horizon; base100: boolean; view: 'level' | 'mom' | 'yoy' }) {
  const { horizon, base100, view } = options;
  const dates = new Set<string>();
  const transformed: Record<string, MacroPoint[]> = {};

  for (const serie of series) {
    let pts = sliceByHorizon(serie.points, horizon);
    if (view === 'mom') pts = monthOverMonth({ ...serie, points: pts });
    else if (view === 'yoy') pts = yearOverYear({ ...serie, points: pts });
    else if (base100) pts = normalizeBase100(pts);

    transformed[serie.id] = pts;
    pts.forEach((p) => dates.add(p.date));
  }

  const sortedDates = Array.from(dates).sort();
  const header = ['date', ...series.map((s) => s.id)].join(',');
  const lines = [header];

  sortedDates.forEach((date) => {
    const row = [date];
    series.forEach((serie) => {
      const value = transformed[serie.id].find((p) => p.date === date)?.value;
      row.push(value == null ? '' : String(Number(value.toFixed(6))));
    });
    lines.push(row.join(','));
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'macro_board.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function MacroBoardWidget({
  title = '📊 Macro Board',
  initialIds = ['CPIAUCSL', 'VIXCLS', 'T10Y2Y', 'UNRATE'],
  initialFreq = 'monthly',
}: {
  title?: string;
  initialIds?: string[];
  initialFreq?: MacroFreq;
}) {
  const [ids, setIds] = useState<string[]>(initialIds);
  const [horizon, setHorizon] = useState<Horizon>('3Y');
  const [frequency, setFrequency] = useState<MacroFreq>(initialFreq);
  const [chartKind, setChartKind] = useState<'area' | 'line' | 'bar'>('area');
  const [view, setView] = useState<'level' | 'mom' | 'yoy'>('level');
  const [base100, setBase100] = useState(false);

  const query = useMacroSeries({ ids, frequency });
  const seriesList = ensureArray(query.data?.series);

  const transformedSeries = useMemo(() => {
    return seriesList.map((serie) => {
      let points = sliceByHorizon(serie.points, horizon);
      if (view === 'mom') points = monthOverMonth({ ...serie, points });
      else if (view === 'yoy') points = yearOverYear({ ...serie, points });
      else if (base100) points = normalizeBase100(points);
      return { ...serie, points };
    });
  }, [seriesList, horizon, base100, view]);

  const chartData = useMemo(() => {
    const dates = new Set<string>();
    transformedSeries.forEach((serie) => {
      serie.points.forEach((point) => dates.add(point.date));
    });
    const sortedDates = Array.from(dates).sort();
    return sortedDates.map((date) => {
      const row: Record<string, any> = { date };
      transformedSeries.forEach((serie) => {
        const value = serie.points.find((point) => point.date === date)?.value;
        row[serie.id] = value == null ? null : Number(value.toFixed(4));
      });
      return row;
    });
  }, [transformedSeries]);

  const categories = useMemo(() => transformedSeries.map((serie) => serie.id), [transformedSeries]);

  return (
    <Card data-testid="macro-board">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            Sélectionne tes séries FRED, ajuste l’horizon, compare Niveau / MoM / YoY, normalise Base 100.
          </Text>
        </div>
        <Group gap="xs" wrap="nowrap">
          <MultiSelect
            aria-label="Séries"
            data={[
              { value: 'CPIAUCSL', label: 'CPI (CPIAUCSL)' },
              { value: 'VIXCLS', label: 'VIX (VIXCLS)' },
              { value: 'T10Y2Y', label: 'Yield 10Y-2Y (T10Y2Y)' },
              { value: 'UNRATE', label: 'Unemployment (UNRATE)' },
              { value: 'FEDFUNDS', label: 'Fed Funds (FEDFUNDS)' },
              { value: 'M2SL', label: 'M2 Money Supply (M2SL)' },
              { value: 'ICSA', label: 'Jobless Claims (ICSA)' },
            ]}
            value={ids}
            onChange={(next) => setIds(next)}
            searchable
            placeholder="Ajouter des séries"
            style={{ minWidth: 320 }}
          />
          <SegmentedControl
            aria-label="Horizon"
            value={horizon}
            onChange={(value) => setHorizon(value as Horizon)}
            data={[{ label:'1Y', value:'1Y' }, { label:'3Y', value:'3Y' }, { label:'5Y', value:'5Y' }, { label:'Max', value:'MAX' }]}
          />
          <Select
            aria-label="Fréquence"
            value={frequency}
            onChange={(value) => setFrequency((value as MacroFreq) ?? 'monthly')}
            data={[
              { value:'daily', label:'Daily' },
              { value:'weekly', label:'Weekly' },
              { value:'monthly', label:'Monthly' },
              { value:'quarterly', label:'Quarterly' },
            ]}
            w={160}
          />
          <SegmentedControl
            aria-label="Vue"
            value={view}
            onChange={(value) => setView(value as 'level' | 'mom' | 'yoy')}
            data={[
              { label:'Niveau', value:'level' },
              { label:'MoM %',  value:'mom' },
              { label:'YoY %',  value:'yoy' },
            ]}
          />
          <Tooltip label="Normalise la première valeur à 100 (vue Niveau seulement)">
            <Switch
              label="Base 100"
              checked={base100}
              onChange={(event) => setBase100(event.currentTarget.checked)}
              disabled={view !== 'level'}
            />
          </Tooltip>
          <Select
            aria-label="Type de graphique"
            value={chartKind}
            onChange={(value) => setChartKind((value as 'area' | 'line' | 'bar') ?? 'area')}
            data={[{ value:'area', label:'Area' }, { value:'line', label:'Line' }, { value:'bar', label:'Bar' }]}
            w={140}
          />
          <Button variant="light" onClick={() => query.refetch()} leftSection={<IconRefresh size={16} />} loading={query.isFetching}>
            Rafraîchir
          </Button>
          <Button variant="light" onClick={() => exportCsv(seriesList, { horizon, base100, view })} leftSection={<IconDownload size={16} />}>
            Export CSV
          </Button>
          <FreshnessBadge freshness={query.data?.updated_at ?? undefined} />
        </Group>
      </Group>

      <Stack mt="md" gap="md">
        {query.isLoading && <Alert color="blue" title="Chargement">Récupération des séries macro…</Alert>}
        {query.error && <Alert color="red" title="Erreur">{String(query.error)}</Alert>}

        {!query.isLoading && !query.error && (
          transformedSeries.length === 0 ? (
            <Alert color="gray" title="Aucune série">Ajoutez des identifiants FRED pour commencer.</Alert>
          ) : (
            <>
              <Divider label="Visualisations" />
              {chartKind === 'area' && (
                <AreaChart className="h-96" data={chartData} index="date" categories={categories} yAxisWidth={56} />
              )}
              {chartKind === 'line' && (
                <LineChart className="h-96" data={chartData} index="date" categories={categories} yAxisWidth={56} />
              )}
              {chartKind === 'bar' && (
                <BarChart className="h-96" data={chartData} index="date" categories={categories} yAxisWidth={56} />
              )}
            </>
          )
        )}
      </Stack>
    </Card>
  );
}
