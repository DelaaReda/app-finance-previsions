import { useMemo, useState } from 'react';
import { Group, MultiSelect, SegmentedControl, Select, Alert, Table, Badge, Tooltip } from '@mantine/core';
import { AreaChart, BarList } from '@tremor/react';
import { IconRefresh, IconDownload, IconArrowUp, IconArrowDown, IconMinus } from '@tabler/icons-react';
import { Button, Card, Title } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import { useForecasts } from '@/hooks/useForecasts';
import { ensureArray } from '@/lib/safe';

function exportCSV(items: any[]) {
  const cols = [
    'ticker',
    'name',
    'sector',
    'horizon',
    'score',
    'direction',
    'confidence',
    'expected_return_pct',
    'model_version',
    'forecasted_at',
    'themes',
  ];
  const lines = [cols.join(',')];
  for (const it of items) {
    const row = cols
      .map((col) => {
        const value = col === 'themes' ? ensureArray(it[col]).join('|') : it[col];
        if (value == null) return '';
        const str = String(value);
        return str.includes(',') || str.includes('"') ? `"${str.replaceAll('"', '""')}"` : str;
      })
      .join(',');
    lines.push(row);
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const anchor = document.createElement('a');
  anchor.href = URL.createObjectURL(blob);
  anchor.download = 'forecasts.csv';
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}

function formatSparkline(items: any[]) {
  return items
    .slice(0, 5)
    .filter((item) => item.ticker)
    .flatMap((item) =>
      ensureArray(item.sparkline).map((point: any) => ({
        date: point.date,
        [item.ticker]: point.value,
      })),
    )
    .reduce((acc: any[], row: Record<string, unknown>) => {
      if (!row.date) return acc;
      const existing = acc.find((entry) => entry.date === row.date);
      if (existing) Object.assign(existing, row);
      else acc.push(row);
      return acc;
    }, []);
}

function percent(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '—';
  return `${value.toFixed(2)}%`;
}

export default function ForecastsProBoard() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [horizon, setHorizon] = useState<string>('short');
  const [themes, setThemes] = useState<string[]>([]);
  const [sort, setSort] = useState<string>('score_desc');

  const { data, isLoading, isFetching, error, refetch } = useForecasts({
    tickers: tickers.length ? tickers : undefined,
    horizons: horizon ? [horizon as any] : undefined,
    themes: themes.length ? themes : undefined,
    limit: 200,
    sort,
  });

  const items = ensureArray(data?.items);

  const avgScore = useMemo(() => {
    const scores = items.map((item: any) => Number(item.score ?? 0)).filter((value) => Number.isFinite(value));
    return scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  }, [items]);

  const up = items.filter((item: any) => item.direction === 'up').length;
  const down = items.filter((item: any) => item.direction === 'down').length;
  const neutral = items.filter((item: any) => item.direction === 'neutral').length;

  return (
    <Card data-testid="forecasts-pro">
      <Group justify="space-between" wrap="wrap">
        <Title order={4}>📈 Forecasts Pro</Title>
        <Group gap="xs" wrap="wrap">
          <MultiSelect
            placeholder="Tickers"
            searchable
            value={tickers}
            onChange={setTickers}
            data={[]}
            w={240}
          />
          <SegmentedControl
            value={horizon}
            onChange={(value) => setHorizon(value)}
            data={[
              { label: 'S', value: 'short' },
              { label: 'M', value: 'medium' },
              { label: 'L', value: 'long' },
            ]}
          />
          <MultiSelect
            placeholder="Themes"
            value={themes}
            onChange={setThemes}
            data={['growth', 'value', 'momentum', 'dividend', 'quality'].map((theme) => ({ value: theme, label: theme }))}
            w={220}
          />
          <Select
            value={sort}
            onChange={(value) => value && setSort(value)}
            w={180}
            data={[
              { value: 'score_desc', label: 'Score ↓' },
              { value: 'expected_return_desc', label: 'Exp. Return ↓' },
              { value: 'confidence_desc', label: 'Confidence ↓' },
            ]}
          />
          <Button variant="light" onClick={() => refetch()} leftSection={<IconRefresh size={16} />} loading={isFetching}>
            Refresh
          </Button>
          <Button variant="light" onClick={() => exportCSV(items)} leftSection={<IconDownload size={16} />}>
            Export CSV
          </Button>
          <FreshnessBadge freshness={data?.updated_at ?? undefined} />
        </Group>
      </Group>

      {isLoading && <Alert color="blue" mt="md">Loading forecasts…</Alert>}
      {error && <Alert color="red" mt="md">Failed to load: {String(error)}</Alert>}

      {!isLoading && !error && (
        <>
          <Group mt="md" gap="lg">
            <Badge size="lg">Avg score: {avgScore.toFixed(1)}</Badge>
            <Badge leftSection={<IconArrowUp size={14} />}>{up} up</Badge>
            <Badge leftSection={<IconArrowDown size={14} />}>{down} down</Badge>
            <Badge leftSection={<IconMinus size={14} />}>{neutral} neutral</Badge>
          </Group>

          <Group mt="lg" grow align="start">
            <div>
              <BarList
                data={items.slice(0, 15).map((item: any) => ({
                  name: `${item.ticker ?? item.symbol} · ${item.horizon}`,
                  value: Math.round(Number(item.score ?? 0)),
                }))}
                valueFormatter={(number) => String(number)}
              />
            </div>
            <div>
              <AreaChart
                data={formatSparkline(items)}
                index="date"
                categories={items
                  .slice(0, 5)
                  .map((item: any) => item.ticker ?? item.symbol)
                  .filter(Boolean)}
                yAxisWidth={56}
              />
            </div>
          </Group>

          <Table mt="lg" striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Ticker</Table.Th>
                <Table.Th>Horizon</Table.Th>
                <Table.Th>Score</Table.Th>
                <Table.Th>Dir</Table.Th>
                <Table.Th>Conf.</Table.Th>
                <Table.Th>Exp. %</Table.Th>
                <Table.Th>Themes</Table.Th>
                <Table.Th>Model</Table.Th>
                <Table.Th>When</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((item: any, index: number) => (
                <Table.Tr key={`${item.ticker ?? item.symbol}-${index}`}>
                  <Table.Td>{item.ticker ?? item.symbol}</Table.Td>
                  <Table.Td>{item.horizon}</Table.Td>
                  <Table.Td>{Number(item.score ?? 0).toFixed(1)}</Table.Td>
                  <Table.Td>{item.direction}</Table.Td>
                  <Table.Td>{Math.round((item.confidence ?? 0) * 100)}%</Table.Td>
                  <Table.Td>{percent(item.expected_return_pct ?? item.expectedReturnPct ?? null)}</Table.Td>
                  <Table.Td>{ensureArray(item.themes).join(', ')}</Table.Td>
                  <Table.Td>{item.model_version ?? '—'}</Table.Td>
                  <Table.Td>
                    {item.forecasted_at ? new Date(item.forecasted_at).toLocaleString() : '—'}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </>
      )}
    </Card>
  );
}
