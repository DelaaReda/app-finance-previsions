import { useMemo, useState } from 'react';
import { AreaChart, LineChart, BarChart } from '@tremor/react';
import {
  Alert,
  Divider,
  Group,
  MultiSelect,
  Select,
  SegmentedControl,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Tooltip,
  Paper,
} from '@mantine/core';
import { IconDownload, IconRefresh, IconInfoCircle } from '@tabler/icons-react';
import { Card, Title, Button, Text, Badge } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import SourceTooltip from '@/components/ui/SourceTooltip';
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

function formatLatest(value: number | null | undefined) {
  if (value == null) return '—';
  const abs = Math.abs(value);
  if (abs >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
  if (abs >= 10) return value.toFixed(1);
  return value.toFixed(2);
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
  const stats = useMemo(() => {
    return transformedSeries.map((serie) => {
      const pts = ensureArray(serie.points);
      const last = pts[pts.length - 1];
      const prev = pts[pts.length - 2];
      return {
        id: serie.id,
        label: serie.name ?? serie.id,
        value: last?.value ?? null,
        delta: percentChange(last?.value ?? null, prev?.value ?? null),
        frequency: serie.frequency ?? null,
      };
    });
  }, [transformedSeries]);

  const glassPanel = {
    background: 'rgba(9,16,33,0.75)',
    border: '1px solid rgba(226,232,240,0.05)',
    backdropFilter: 'blur(18px)',
  };

  return (
    <Card style={glassPanel}>
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Group gap="8px">
            <Title order={4}>{title}</Title>
            <SourceTooltip 
              source="FRED Economic Data"
              lastUpdate={new Date().toISOString()}
              metadata={{ 
                service: 'FRED API', 
                coverage: 'US Economic Indicators',
                update_frequency: 'Daily'
              }}
            />
          </Group>
          <Text c="dimmed" mt={4}>
            Sélectionne tes séries FRED, ajuste l'horizon, compare Niveau / MoM / YoY, normalise Base 100.
          </Text>
        </div>
        <Group gap="xs" wrap="nowrap">
          <FreshnessBadge freshness={query.data?.updated_at ?? undefined} />
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
        </Group>
      </Group>

      {stats.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} mt="lg" spacing="md">
          {stats.map((stat) => (
            <Paper key={stat.id} p="md" radius="lg" style={glassPanel}>
              <Group justify="space-between" align="flex-start">
                <div>
                  <Group gap="6px">
                    <Badge size="sm" variant="light">
                      {stat.id}
                    </Badge>
                    <SourceTooltip 
                      source="FRED Economic Data"
                      lastUpdate={new Date().toISOString()}
                      metadata={{ 
                        series_id: stat.id,
                        source: 'FRED API',
                        last_refresh: query.data?.updated_at || new Date().toISOString()
                      }}
                    />
                  </Group>
                  <Text fw={600} mt={6}>
                    {stat.label}
                  </Text>
                </div>
                {stat.frequency && (
                  <Text size="xs" c="dimmed">
                    {stat.frequency}
                  </Text>
                )}
              </Group>
              <Text fz="xl" fw={700} mt="sm">
                {formatLatest(stat.value)}
              </Text>
              <Text size="sm" c={stat.delta == null ? 'dimmed' : stat.delta >= 0 ? 'teal.4' : 'red.4'}>
                {stat.delta == null ? '—' : `${stat.delta >= 0 ? '+' : ''}${stat.delta.toFixed(2)}% vs prev`}
              </Text>
            </Paper>
          ))}
        </SimpleGrid>
      )}

      <Stack mt="md" gap="md">
        {query.isLoading && <Skeleton height={360} radius="lg" />}
        {query.error && <Alert color="red" title="Erreur">{String(query.error)}</Alert>}

        {!query.isLoading && !query.error && (
          transformedSeries.length === 0 ? (
            <Alert color="gray" title="Aucune série">Ajoutez des identifiants FRED pour commencer.</Alert>
          ) : (
            <>
              <Divider label="Visualisations" />
              <Paper radius="lg" p="md" style={glassPanel}>
                {chartKind === 'area' && (
                  <AreaChart className="h-96" data={chartData} index="date" categories={categories} yAxisWidth={56} />
                )}
                {chartKind === 'line' && (
                  <LineChart className="h-96" data={chartData} index="date" categories={categories} yAxisWidth={56} />
                )}
                {chartKind === 'bar' && (
                  <BarChart className="h-96" data={chartData} index="date" categories={categories} yAxisWidth={56} />
                )}
              </Paper>
            </>
          )
        )}
      </Stack>
    </Card>
  );
}
