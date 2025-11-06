import { useMemo, useState } from 'react';
import { AreaChart } from '@tremor/react';
import {
  Alert,
  Badge,
  Divider,
  Group,
  MultiSelect,
  ScrollArea,
  Stack,
  TextInput,
  Tooltip,
} from '@mantine/core';
import { IconArrowDownRight, IconArrowUpRight, IconExternalLink, IconMinus } from '@tabler/icons-react';
import { Card, Title, Button, Text } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import {
  useForecastMatrix,
  buildForecastMatrix,
  type MatrixHorizon,
  type ForecastMatrixRow,
} from '@/hooks/useForecasts';
import { ensureArray } from '@/lib/safe';

const HORIZON_OPTIONS: { label: string; value: MatrixHorizon }[] = [
  { label: '1m', value: '1m' },
  { label: '3m', value: '3m' },
  { label: '6m', value: '6m' },
  { label: '12m', value: '12m' },
];

type Props = {
  title?: string;
  defaultUniverse?: string[];
  defaultHorizons?: MatrixHorizon[];
  onAnalyzeSymbol?: (symbol: string) => void;
  onBacktestSymbol?: (symbol: string) => void;
};

function directionIcon(direction?: string) {
  if (direction === 'up') return <IconArrowUpRight size={16} />;
  if (direction === 'down') return <IconArrowDownRight size={16} />;
  return <IconMinus size={16} />;
}

function directionColor(direction?: string): 'teal' | 'red' | 'gray' {
  if (direction === 'up') return 'teal';
  if (direction === 'down') return 'red';
  return 'gray';
}

function pct(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '—';
  const rounded = Math.round(value * 100) / 100;
  return `${rounded}%`;
}

function exportCsv(rows: ForecastMatrixRow[], horizons: MatrixHorizon[]) {
  const header = [
    'symbol',
    'name',
    ...horizons.map((h) => `${h}_score`),
    ...horizons.map((h) => `${h}_direction`),
    ...horizons.map((h) => `${h}_confidence`),
    ...horizons.map((h) => `${h}_expected_return`),
  ];
  const lines = [header.join(',')];

  rows.forEach((row) => {
    const parts: (string | number | undefined | null)[] = [row.symbol, row.name.replaceAll(',', ' ')];
    horizons.forEach((h) => parts.push(row.cells[h]?.score));
    horizons.forEach((h) => parts.push(row.cells[h]?.direction));
    horizons.forEach((h) => parts.push(row.cells[h]?.confidence));
    horizons.forEach((h) => parts.push(row.cells[h]?.expected_return));
    lines.push(parts.map((value) => (value == null ? '' : String(value))).join(','));
  });

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'forecast_matrix.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ForecastMatrixWidget({
  title = '📈 Forecast Matrix',
  defaultUniverse = ['SPY', 'QQQ', 'AAPL', 'NVDA'],
  defaultHorizons = ['1m', '3m', '6m'],
  onAnalyzeSymbol,
  onBacktestSymbol,
}: Props) {
  const [universeInput, setUniverseInput] = useState(defaultUniverse.join(','));
  const [horizons, setHorizons] = useState<MatrixHorizon[]>(defaultHorizons);

  const universe = useMemo(
    () => universeInput.split(',').map((value) => value.trim()).filter(Boolean),
    [universeInput],
  );

  const query = useForecastMatrix({ universe, horizons });
  const rows = useMemo(
    () => buildForecastMatrix(query.data?.items ?? [], horizons),
    [query.data?.items, horizons],
  );

  return (
    <Card data-testid="forecast-matrix">
      <Group justify="space-between" align="center">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            Prévisions multi-horizons (scores, directions, confiance, expected return) pour chaque ticker.
          </Text>
        </div>
        <Group gap="xs" wrap="nowrap">
          <MultiSelect
            label="Horizons"
            data={HORIZON_OPTIONS}
            value={horizons}
            onChange={(values) => setHorizons(ensureArray(values) as MatrixHorizon[])}
            searchable
            style={{ minWidth: 220 }}
          />
          <TextInput
            label="Univers"
            value={universeInput}
            onChange={(event) => setUniverseInput(event.currentTarget.value)}
            placeholder="SPY,QQQ,AAPL,NVDA"
            style={{ width: 280 }}
          />
          <Button onClick={() => query.refetch()} loading={query.isFetching}>Rafraîchir</Button>
          <Button variant="light" onClick={() => exportCsv(rows, horizons)}>Exporter CSV</Button>
          <FreshnessBadge freshness={query.data?.updated_at ?? undefined} />
        </Group>
      </Group>

      {query.isLoading && (
        <Alert mt="md" color="blue" title="Chargement">
          Récupération des prévisions…
        </Alert>
      )}

      {query.error && (
        <Alert mt="md" color="red" title="Erreur">
          Impossible de récupérer les prévisions ({String(query.error)})
        </Alert>
      )}

      {!query.isLoading && !query.error && (
        rows.length === 0 ? (
          <Alert mt="md" color="gray" title="Aucune donnée">
            Pas de prévisions disponibles pour cet univers/horizons.
          </Alert>
        ) : (
          <ScrollArea mt="md" style={{ maxHeight: 560 }} type="always">
            <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
              <thead>
                <tr>
                  <th style={{ position: 'sticky', top: 0, background: 'var(--mantine-color-body)', textAlign: 'left', padding: '8px' }}>Symbole</th>
                  <th style={{ position: 'sticky', top: 0, background: 'var(--mantine-color-body)', textAlign: 'left', padding: '8px' }}>Nom</th>
                  {horizons.map((horizon) => (
                    <th
                      key={horizon}
                      style={{ position: 'sticky', top: 0, background: 'var(--mantine-color-body)', textAlign: 'left', padding: '8px' }}
                    >
                      {horizon}
                    </th>
                  ))}
                  <th style={{ position: 'sticky', top: 0, background: 'var(--mantine-color-body)', textAlign: 'right', padding: '8px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.symbol} style={{ borderBottom: '1px solid var(--mantine-color-dark-6)' }}>
                    <td style={{ padding: '10px 8px', whiteSpace: 'nowrap' }}>
                      <Badge variant="light">{row.symbol}</Badge>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <Text size="sm" c="dimmed">{row.name}</Text>
                    </td>
                    {horizons.map((horizon) => {
                      const cell = row.cells[horizon];
                      if (!cell) {
                        return (
                          <td key={horizon} style={{ padding: '10px 8px' }}>
                            <Badge variant="light" color="gray">—</Badge>
                          </td>
                        );
                      }
                      return (
                        <td key={horizon} style={{ padding: '10px 8px', minWidth: 220 }}>
                          <Stack gap={6}>
                            <Group gap={6}>
                              <Badge
                                variant="light"
                                color={directionColor(cell.direction)}
                                leftSection={directionIcon(cell.direction)}
                              >
                                {Math.round(cell.score)}
                              </Badge>
                              <Tooltip label="Confiance">
                                <Badge variant="outline" color="gray">{Math.round(cell.confidence ?? 0)}%</Badge>
                              </Tooltip>
                              <Tooltip label="Expected return">
                                <Badge variant="outline" color="gray">{pct(cell.expected_return)}</Badge>
                              </Tooltip>
                            </Group>
                            {ensureArray(cell.spark).length > 0 && (
                              <AreaChart
                                className="h-10"
                                data={ensureArray(cell.spark).map((value, index) => ({ index, value }))}
                                index="index"
                                categories={['value']}
                                showLegend={false}
                                showGridLines={false}
                                showYAxis={false}
                                showXAxis={false}
                                autoMinValue
                              />
                            )}
                          </Stack>
                        </td>
                      );
                    })}
                    <td style={{ padding: '10px 8px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                      <Group gap="xs" justify="right">
                        <Button
                          size="xs"
                          variant="light"
                          leftSection={<IconExternalLink size={14} />}
                          onClick={() => {
                            if (onAnalyzeSymbol) onAnalyzeSymbol(row.symbol);
                            else window.location.assign(`/stocks?symbol=${encodeURIComponent(row.symbol)}`);
                          }}
                          data-testid={`forecast-matrix-analyze-${row.symbol}`}
                        >
                          Analyser
                        </Button>
                        <Button
                          size="xs"
                          variant="subtle"
                          onClick={() => {
                            if (onBacktestSymbol) onBacktestSymbol(row.symbol);
                            else window.location.assign(`/backtests?symbol=${encodeURIComponent(row.symbol)}`);
                          }}
                          data-testid={`forecast-matrix-backtest-${row.symbol}`}
                        >
                          Backtester
                        </Button>
                      </Group>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Divider mt="sm" />
          </ScrollArea>
        )
      )}
    </Card>
  );
}
