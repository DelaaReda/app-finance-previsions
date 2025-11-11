import { useState } from 'react';
import { Card, Title, Text, Button } from '@/ui';
import { Alert, Grid, Group, Loader, SegmentedControl } from '@mantine/core';
import { BarList } from '@tremor/react';
import { useMovers, type MoversWindow } from '@/hooks/useMovers';

type Props = {
  universe: string[];
  initialWindow?: MoversWindow;
  limitTop?: number;
  limitBottom?: number;
  title?: string;
  description?: string;
  onSelectTicker?: (ticker: string) => void;
};

function formatPct(value: number) {
  return `${(value * 100).toFixed(2)}%`;
}

export function SignalBarsWidget({
  universe,
  initialWindow = '1d',
  limitTop = 10,
  limitBottom = 10,
  title = 'Top / Bottom movers',
  description = 'Variation par période (rendement %)',
  onSelectTicker,
}: Props) {
  const [window, setWindow] = useState<MoversWindow>(initialWindow);
  const { data, isLoading, isFetching, error, refetch } = useMovers(universe, window, Math.max(limitTop, limitBottom));

  if (isLoading) {
    return (
      <Card>
        <Group justify="space-between" mb="xs">
          <Title order={4}>{title}</Title>
          <Group gap="xs">
            <Loader size="sm" />
            <Text>Chargement…</Text>
          </Group>
        </Group>
        {description && <Text c="dimmed">{description}</Text>}
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <Group justify="space-between" mb="xs">
          <Title order={4}>{title}</Title>
          <Button variant="light" onClick={() => refetch()}>
            Réessayer
          </Button>
        </Group>
        <Alert color="red" title="Erreur">
          Impossible de récupérer les variations ({String(error)})
        </Alert>
      </Card>
    );
  }

  const top = (data?.top ?? []).slice(0, limitTop);
  const bottom = (data?.bottom ?? []).slice(0, limitBottom);

  const topMap = new Map<string, string>();
  const bottomMap = new Map<string, string>();

  const buildItems = (items: typeof top, map: Map<string, string>) =>
    items.map((item) => {
      const label = `${item.ticker} — ${item.label} (${formatPct(item.r)})`;
      map.set(label, item.ticker);
      return {
        name: label,
        value: Math.abs(item.r * 100),
      };
    });

  const topData = buildItems(top, topMap);
  const bottomData = buildItems(bottom, bottomMap);

  const handleSelect = (value: string | null) => {
    if (!value || !onSelectTicker) return;
    const ticker = topMap.get(value) ?? bottomMap.get(value);
    if (ticker) onSelectTicker(ticker);
  };

  const exportCsv = () => {
    const lines = ['side,ticker,label,return_pct'];
    const escape = (value: string) => value.replace(/"/g, '""');
    top.forEach((entry) => {
      lines.push(`top,${entry.ticker},"${escape(entry.label)}",${(entry.r * 100).toFixed(4)}`);
    });
    bottom.forEach((entry) => {
      lines.push(`bottom,${entry.ticker},"${escape(entry.label)}",${(entry.r * 100).toFixed(4)}`);
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `movers-${window}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <Group justify="space-between" align="center" mb="xs">
        <div>
          <Title order={4}>{title}</Title>
          {description && (
            <Text c="dimmed" mt={4}>
              {description}
            </Text>
          )}
        </div>
        <Group gap="xs">
          <SegmentedControl
            value={window}
            onChange={(value) => setWindow(value as MoversWindow)}
            data={[
              { label: '1D', value: '1d' },
              { label: '1W', value: '1w' },
              { label: '1M', value: '1m' },
              { label: '3M', value: '3m' },
              { label: '6M', value: '6m' },
              { label: '1Y', value: '1y' },
            ]}
          />
          <Button variant="light" onClick={exportCsv}>
            Exporter CSV
          </Button>
          <Button onClick={() => refetch()} loading={isFetching}>
            Rafraîchir
          </Button>
        </Group>
      </Group>

      {topData.length === 0 && bottomData.length === 0 ? (
        <Alert>Aucune variation disponible pour l’univers sélectionné.</Alert>
      ) : (
        <Grid gutter="md">
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Text fw={600} mb="xs">
              Top gagnants
            </Text>
            <BarList
              data={topData as any}
              valueFormatter={(value: number) => value.toFixed(2) + '%'}
              showAnimation
              onValueChange={
                onSelectTicker
                  ? (val: string | number | null) => handleSelect(val == null ? null : String(val))
                  : undefined
              }
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 6 }}>
            <Text fw={600} mb="xs">
              Top perdants
            </Text>
            <BarList
              data={bottomData as any}
              valueFormatter={(value: number) => `-${value.toFixed(2)}%`}
              showAnimation
              onValueChange={
                onSelectTicker
                  ? (val: string | number | null) => handleSelect(val == null ? null : String(val))
                  : undefined
              }
            />
          </Grid.Col>
        </Grid>
      )}
    </Card>
  );
}
