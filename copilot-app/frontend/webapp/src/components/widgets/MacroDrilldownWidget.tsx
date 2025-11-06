import { useMemo, useState } from 'react';
import { LineChart } from '@tremor/react';
import { IconDownload } from '@tabler/icons-react';
import { Alert, Group, MultiSelect, SegmentedControl, Stack, Switch } from '@mantine/core';
import { Card, Title, Button, Text } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import {
  useMacroSeries,
  toWideTable,
  type MacroRange,
  type MacroFreq,
} from '@/hooks/useMacroSeries';
import { ensureArray } from '@/lib/safe';

type Option = { label: string; value: string };

const DEFAULT_SERIES: Option[] = [
  { label: 'CPI (CPIAUCSL)', value: 'CPIAUCSL' },
  { label: 'VIX (VIXCLS)', value: 'VIXCLS' },
  { label: '10Y-2Y (T10Y2Y)', value: 'T10Y2Y' },
  { label: 'Unemployment (UNRATE)', value: 'UNRATE' },
  { label: 'ISM Manufacturing PMI', value: 'ISM/MAN_PMI' },
  { label: 'Initial Jobless Claims', value: 'ICSA' },
];

const RANGE_OPTIONS: { label: string; value: MacroRange }[] = [
  { label: '1Y', value: '1y' },
  { label: '3Y', value: '3y' },
  { label: '5Y', value: '5y' },
  { label: '10Y', value: '10y' },
  { label: 'MAX', value: 'max' },
];

const FREQ_OPTIONS: { label: string; value: MacroFreq }[] = [
  { label: 'Monthly', value: 'monthly' },
  { label: 'Weekly', value: 'weekly' },
  { label: 'Daily', value: 'daily' },
  { label: 'Quarterly', value: 'quarterly' },
];

function downloadCsv(rows: Record<string, any>[]) {
  if (!rows.length) return;
  const columns = Object.keys(rows[0]);
  const lines = [columns.join(',')];
  rows.forEach((row) => {
    lines.push(columns.map((column) => (row[column] ?? '')).join(','));
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'macro_series.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function MacroDrilldownWidget({
  title = '🧭 Macro Drilldown',
  initialSeries = ['CPIAUCSL', 'VIXCLS', 'T10Y2Y'],
  initialRange = '5y',
  initialFreq = 'monthly',
}: {
  title?: string;
  initialSeries?: string[];
  initialRange?: MacroRange;
  initialFreq?: MacroFreq;
}) {
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSeries);
  const [range, setRange] = useState<MacroRange>(initialRange);
  const [freq, setFreq] = useState<MacroFreq>(initialFreq);
  const [normalize, setNormalize] = useState(false);

  const query = useMacroSeries({ ids: selectedIds, range, freq });

  const table = useMemo(
    () => toWideTable(ensureArray(query.data?.series), { normalize }),
    [query.data?.series, normalize],
  );

  const categories = useMemo(() => ensureArray(query.data?.series).map((serie) => serie.id), [query.data?.series]);

  const valueFormatter = (value: number) => {
    if (value == null) return '—';
    if (Math.abs(value) >= 1000) {
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    return value.toFixed(2);
  };

  return (
    <Card data-testid="macro-drilldown">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            Compare des séries macro, ajuste plage & fréquence, normalise (Index=100) pour comparer les tendances.
          </Text>
        </div>
        <Group gap="xs" wrap="nowrap">
          <MultiSelect
            aria-label="Séries macro"
            data={DEFAULT_SERIES}
            searchable
            placeholder="Ajouter des séries (FRED IDs)"
            value={selectedIds}
            onChange={(values) => setSelectedIds(ensureArray(values))}
            style={{ minWidth: 280 }}
          />
          <SegmentedControl
            aria-label="Plage"
            value={range}
            onChange={(value) => setRange(value as MacroRange)}
            data={RANGE_OPTIONS}
          />
          <SegmentedControl
            aria-label="Fréquence"
            value={freq}
            onChange={(value) => setFreq(value as MacroFreq)}
            data={FREQ_OPTIONS}
          />
          <Switch
            aria-label="Normaliser Index 100"
            label="Index=100"
            checked={normalize}
            onChange={(event) => setNormalize(event.currentTarget.checked)}
          />
          <Button onClick={() => query.refetch()} loading={query.isFetching}>
            Rafraîchir
          </Button>
          <Button variant="light" leftSection={<IconDownload size={16} />} onClick={() => downloadCsv(table)}>
            Export CSV
          </Button>
          <FreshnessBadge freshness={query.data?.updated_at ?? undefined} />
        </Group>
      </Group>

      {query.isLoading && (
        <Alert mt="md" color="blue" title="Chargement">
          Récupération des séries macro…
        </Alert>
      )}

      {query.error && (
        <Alert mt="md" color="red" title="Erreur">
          Impossible de charger les séries macro ({String(query.error)})
        </Alert>
      )}

      {!query.isLoading && !query.error && (
        table.length === 0 ? (
          <Alert mt="md" color="gray" title="Aucune donnée">
            Aucune donnée pour cet ensemble de paramètres.
          </Alert>
        ) : (
          <Stack mt="md" gap="md">
            <LineChart
              className="h-80"
              data={table}
              index="date"
              categories={categories}
              showLegend
              valueFormatter={valueFormatter}
              showXAxis
              showGridLines
              yAxisWidth={56}
            />
          </Stack>
        )
      )}
    </Card>
  );
}
