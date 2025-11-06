import { useMemo, useState } from 'react';
import { AreaChart } from '@tremor/react';
import {
  Alert,
  Badge,
  Card as MantineCard,
  Divider,
  Grid,
  Group,
  SegmentedControl,
  Stack,
  Tooltip,
} from '@mantine/core';
import { Card, Title, Text, Button } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import {
  useMacroSeries,
  useMacroSignals,
  lastDelta,
  type MacroId,
  type RangeOpt,
} from '@/hooks/useMacro';
import { ensureArray } from '@/lib/safe';

const DEFAULT_IDS: { id: MacroId; label: string; unitHint?: string }[] = [
  { id: 'CPIAUCSL', label: 'Inflation (CPI)', unitHint: '% A/A' },
  { id: 'VIXCLS', label: 'VIX (Volatilité)', unitHint: 'index' },
  { id: 'T10Y2Y', label: 'Courbe 10Y-2Y', unitHint: 'pp' },
  { id: 'UNRATE', label: 'Chômage', unitHint: '%' },
];

function formatNumber(value?: number, unitHint?: string) {
  if (value == null) return '—';
  const normalized = Math.abs(value) >= 100 ? value.toFixed(0) : Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(2);
  return unitHint ? `${normalized} ${unitHint}` : normalized;
}

function deltaBadgeColor(delta?: number) {
  if (delta == null) return 'gray';
  if (delta > 0) return 'teal';
  if (delta < 0) return 'red';
  return 'gray';
}

function exportCsv(series: Map<MacroId, { name: string; points: { date: string; value: number }[] }>) {
  const dates = new Set<string>();
  series.forEach((serie) => {
    serie.points.forEach((point) => dates.add(point.date));
  });
  const orderedDates = Array.from(dates).sort();
  const header = ['date', ...series.keys()].join(',');
  const lines = [header];
  orderedDates.forEach((date) => {
    const row = [date];
    series.forEach((serie) => {
      const point = serie.points.find((p) => p.date === date);
      row.push(point?.value ?? '');
    });
    lines.push(row.join(','));
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'macro-board.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

type MacroBoardWidgetProps = {
  title?: string;
  ids?: { id: MacroId; label: string; unitHint?: string }[];
  defaultRange?: RangeOpt;
};

export function MacroBoardWidget({
  title = '📈 Macro Board',
  ids = DEFAULT_IDS,
  defaultRange = '3y',
}: MacroBoardWidgetProps) {
  const [range, setRange] = useState<RangeOpt>(defaultRange);
  const macroIds = ids.map((item) => item.id);

  const seriesQuery = useMacroSeries({ ids: macroIds, range });
  const signalsQuery = useMacroSignals();

  const seriesById = seriesQuery.data?.byId ?? new Map();
  const freshness = useMemo(() => {
    const updates = ensureArray(seriesQuery.data?.items)
      .map((item) => item.updatedAt)
      .filter(Boolean) as string[];
    if (!updates.length) return undefined;
    return updates.sort().slice(-1)[0];
  }, [seriesQuery.data]);

  const exportable = useMemo(() => {
    const map = new Map<MacroId, { name: string; points: { date: string; value: number }[] }>();
    ids.forEach((config) => {
      const serie = seriesById.get(config.id);
      if (serie && serie.points.length) {
        map.set(config.id, { name: serie.name, points: serie.points });
      }
    });
    return map;
  }, [ids, seriesById]);

  return (
    <Card>
      <Group justify="space-between" align="center">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            CPI, VIX, courbe 10Y-2Y, chômage + signaux macro (récession, inversion, volatilité).
          </Text>
        </div>
        <Group gap="xs">
          <SegmentedControl
            value={range}
            onChange={(value) => setRange(value as RangeOpt)}
            data={[
              { label: '1 an', value: '1y' },
              { label: '3 ans', value: '3y' },
              { label: '5 ans', value: '5y' },
              { label: 'Max', value: 'max' },
            ]}
          />
          <Button onClick={() => seriesQuery.refetch()} loading={seriesQuery.isFetching}>
            Rafraîchir
          </Button>
          <Button variant="light" onClick={() => exportCsv(exportable)}>
            Exporter CSV
          </Button>
          <FreshnessBadge freshness={freshness} />
        </Group>
      </Group>

      {seriesQuery.isLoading && (
        <Alert mt="md" color="blue" title="Chargement">
          Récupération des séries…
        </Alert>
      )}
      {seriesQuery.error && (
        <Alert mt="md" color="red" title="Erreur">
          Impossible de récupérer les séries ({String(seriesQuery.error)})
        </Alert>
      )}

      {!seriesQuery.isLoading && !seriesQuery.error && (
        <>
          <Grid mt="md">
            {ids.map((config) => {
              const serie = seriesById.get(config.id);
              const deltas = lastDelta(serie);
              const badgeColor = deltaBadgeColor(deltas.delta);
              const chartData = ensureArray(serie?.points).map((point) => ({
                date: point.date,
                value: point.value,
              }));

              return (
                <Grid.Col key={config.id} span={{ base: 12, sm: 6, lg: 3 }}>
                  <MantineCard withBorder radius="lg" shadow="sm">
                    <Stack gap="xs">
                      <Group justify="space-between" align="center">
                        <Text fw={600}>{config.label}</Text>
                        {serie?.unit && (
                          <Badge variant="light">{serie.unit}</Badge>
                        )}
                      </Group>
                      <Group gap="xs" align="baseline">
                        <Text fw={700} size="xl">
                          {formatNumber(deltas.last, config.unitHint)}
                        </Text>
                        <Badge color={badgeColor} variant="light">
                          {deltas.delta == null
                            ? '—'
                            : deltas.delta > 0
                            ? `+${formatNumber(deltas.delta)}`
                            : `${formatNumber(deltas.delta)}`}
                        </Badge>
                      </Group>
                      {chartData.length > 1 ? (
                        <AreaChart
                          className="h-28"
                          data={chartData}
                          index="date"
                          categories={['value']}
                          showLegend={false}
                          showGridLines={false}
                          showYAxis={false}
                          showXAxis={false}
                          curveType="monotone"
                          valueFormatter={(value: number) => formatNumber(value)}
                        />
                      ) : (
                        <Alert color="gray" variant="light">
                          Pas assez de points pour tracer.
                        </Alert>
                      )}
                    </Stack>
                  </MantineCard>
                </Grid.Col>
              );
            })}
          </Grid>

          <Divider my="md" />

          <MantineCard withBorder radius="lg" shadow="sm">
            <Title order={5} mb="xs">
              🧭 Signaux Macro
            </Title>
            {!signalsQuery.data?.signals?.length && (
              <Alert color="gray" variant="light">
                Aucun signal disponible pour le moment.
              </Alert>
            )}
            <Stack gap="xs">
              {ensureArray(signalsQuery.data?.signals).map((signal) => {
                const color =
                  signal.severity === 'high'
                    ? 'red'
                    : signal.severity === 'medium'
                    ? 'yellow'
                    : signal.severity === 'low'
                    ? 'teal'
                    : 'gray';
                return (
                  <Group key={signal.key} justify="space-between" wrap="nowrap" align="flex-start">
                    <Group gap="sm" wrap="nowrap">
                      <Badge color={color} variant="filled" radius="sm" tt="capitalize" w={90} ta="center">
                        {signal.severity}
                      </Badge>
                      <Stack gap={2} maw={420}>
                        <Text fw={600}>{signal.name}</Text>
                        {signal.description && (
                          <Text c="dimmed" size="sm" lineClamp={2}>
                            {signal.description}
                          </Text>
                        )}
                      </Stack>
                    </Group>
                    <Group gap="xs">
                      {signal.value != null && (
                        <Tooltip label="Valeur du signal">
                          <Badge variant="light">{String(signal.value)}</Badge>
                        </Tooltip>
                      )}
                      {signal.metric_id && (
                        <Badge variant="light">{signal.metric_id}</Badge>
                      )}
                    </Group>
                  </Group>
                );
              })}
            </Stack>
            <Group justify="space-between" mt="sm">
              <Text c="dimmed" size="xs">
                Mises à jour : {signalsQuery.data?.updatedAt ? new Date(signalsQuery.data.updatedAt).toLocaleString() : '—'}
              </Text>
              <Text c="dimmed" size="xs">
                {new Date().toLocaleTimeString()}
              </Text>
            </Group>
          </MantineCard>
        </>
      )}
    </Card>
  );
}
