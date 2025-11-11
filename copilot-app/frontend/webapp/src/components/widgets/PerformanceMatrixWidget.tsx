import { useMemo, useState } from 'react';
import {
  Alert,
  Group,
  MultiSelect,
  ScrollArea,
  SegmentedControl,
  Stack,
  Tooltip,
  rem,
} from '@mantine/core';
import { Card, Title, Text, Button, Badge } from '@/ui';
import { usePerformanceMatrix, type Horizon } from '@/hooks/usePerformanceMatrix';

function clamp(val: number, min: number, max: number) {
  return Math.min(Math.max(val, min), max);
}

function valueToColor(v?: number): string {
  if (v == null) return 'var(--mantine-color-dark-6)';
  if (Number.isNaN(v)) return 'var(--mantine-color-dark-6)';
  const normalized = clamp(v, -10, 10);
  if (Math.abs(normalized) < 0.15) return 'rgba(148,163,184,0.25)';
  const hue = Math.round(((normalized + 10) / 20) * 140);
  return `hsl(${hue} 65% 45% / 0.85)`;
}

function fmtPct(v?: number) {
  if (v == null || Number.isNaN(v)) return '—';
  const sign = v > 0 ? '+' : v < 0 ? '−' : '';
  return `${sign}${Math.abs(v).toFixed(2)}%`;
}

type Props = {
  title?: string;
  universe?: string[];
  defaultHorizons?: Horizon[];
  sectorOptions?: string[];
  themeOptions?: string[];
  onSelectTicker?: (ticker: string) => void;
};

export function PerformanceMatrixWidget({
  title = 'Performance Matrix',
  universe = [],
  defaultHorizons = ['short', 'medium', 'long'],
  sectorOptions = [],
  themeOptions = [],
  onSelectTicker,
}: Props) {
  const [horizons, setHorizons] = useState<Horizon[]>(defaultHorizons);
  const [sectors, setSectors] = useState<string[]>([]);
  const [themes, setThemes] = useState<string[]>([]);

  const query = usePerformanceMatrix({
    horizons,
    tickers: universe,
    sectors,
    themes,
  });

  const rows = useMemo(() => {
    const items = query.data ?? [];
    const score = (row: (typeof items)[number]) => {
      const vals = horizons
        .map((h) => row.values[h])
        .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
      if (!vals.length) return Number.NEGATIVE_INFINITY;
      return vals.reduce((acc, curr) => acc + curr, 0) / vals.length;
    };
    return [...items].sort((a, b) => score(b) - score(a));
  }, [query.data, horizons]);

  const exportCsv = () => {
    const header = ['ticker', 'name', 'sector', 'themes', ...horizons.map((h) => `value_${h}`), 'updated_at'];
    const lines = [header.join(',')];
    rows.forEach((row) => {
      lines.push([
        row.ticker,
        `"${row.name.replaceAll('"', '""')}"`,
        row.sector ?? '',
        `"${row.themes.join('|').replaceAll('"', '""')}"`,
        ...horizons.map((h) => (row.values[h] ?? '')),
        row.updatedAt ?? '',
      ].join(','));
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'performance-matrix.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <Group justify="space-between" align="center" mb="xs">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            Heatmap multi-horizons — clic sur une cellule ou un ticker pour ouvrir la fiche.
          </Text>
        </div>
        <Group gap="xs">
          <SegmentedControl
            multiple
            data={[
              { label: 'Court', value: 'short' },
              { label: 'Moyen', value: 'medium' },
              { label: 'Long', value: 'long' },
            ]}
            value={horizons}
            onChange={(values) => setHorizons(values as Horizon[])}
          />
          <Button variant="light" onClick={exportCsv}>
            Exporter CSV
          </Button>
          <Button onClick={() => query.refetch()} loading={query.isFetching}>
            Rafraîchir
          </Button>
        </Group>
      </Group>

      <Group align="center" wrap="wrap" gap="md" mb="md">
        <MultiSelect
          label="Secteurs"
          data={sectorOptions.map((value) => ({ value, label: value }))}
          value={sectors}
          onChange={setSectors}
          searchable
          clearable
          placeholder="Tous"
          w={320}
        />
        <MultiSelect
          label="Thèmes"
          data={themeOptions.map((value) => ({ value, label: value }))}
          value={themes}
          onChange={setThemes}
          searchable
          clearable
          placeholder="Tous"
          w={360}
        />
        <Badge variant="light">{rows.length} lignes</Badge>
      </Group>

      {query.isLoading && <Alert color="blue">Chargement de la matrice…</Alert>}
      {query.error && <Alert color="red">Impossible de récupérer la matrice ({String(query.error)})</Alert>}
      {!query.isLoading && !query.error && rows.length === 0 && (
        <Alert color="gray">Aucune donnée pour ces filtres.</Alert>
      )}

      {!query.isLoading && !query.error && rows.length > 0 && (
        <ScrollArea h={rem(420)} type="auto">
          <div role="grid" aria-label="Performance matrix">
            <div
              role="row"
              style={{
                display: 'grid',
                gridTemplateColumns: `220px repeat(${horizons.length}, 120px)`,
                fontWeight: 600,
                padding: '6px 8px',
                borderBottom: '1px solid var(--mantine-color-dark-6)',
              }}
            >
              <div role="columnheader">Ticker</div>
              {horizons.map((h) => (
                <div key={h} role="columnheader" style={{ textTransform: 'capitalize' }}>
                  {h}
                </div>
              ))}
            </div>

            {rows.map((row) => (
              <div
                key={row.ticker}
                role="row"
                style={{
                  display: 'grid',
                  gridTemplateColumns: `220px repeat(${horizons.length}, 120px)`,
                  borderBottom: '1px solid var(--mantine-color-dark-7)',
                  alignItems: 'stretch',
                }}
              >
                <div role="gridcell" style={{ padding: '8px' }}>
                  <Stack gap={2}>
                    <Group gap={8}>
                      <Text
                        fw={600}
                        style={{ cursor: onSelectTicker ? 'pointer' : 'default' }}
                        onClick={() => onSelectTicker?.(row.ticker)}
                      >
                        {row.ticker}
                      </Text>
                      {row.sector && <Badge variant="light">{row.sector}</Badge>}
                    </Group>
                    <Text c="dimmed" size="sm" lineClamp={1}>
                      {row.name}
                    </Text>
                  </Stack>
                </div>

                {horizons.map((horizon) => {
                  const value = row.values[horizon];
                  const color = valueToColor(value);
                  return (
                    <Tooltip key={`${row.ticker}-${horizon}`} label={`${row.ticker} • ${horizon} • ${fmtPct(value)}`}>
                      <div
                        role="gridcell"
                        onClick={() => onSelectTicker?.(row.ticker)}
                        style={{
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: '8px',
                          background: color,
                          color: 'white',
                          userSelect: 'none',
                        }}
                      >
                        <span style={{ fontWeight: 700 }}>{fmtPct(value)}</span>
                      </div>
                    </Tooltip>
                  );
                })}
              </div>
            ))}
          </div>
        </ScrollArea>
      )}

      <Group justify="space-between" mt="sm">
        <Text c="dimmed" size="xs">
          Rouge = sous-performance, Vert = surperformance (normalisé). Valeurs en pourcentage nets.
        </Text>
        <Text c="dimmed" size="xs">
          {new Date().toLocaleTimeString()} • {query.isFetching ? 'Actualisation…' : 'À jour'}
        </Text>
      </Group>
    </Card>
  );
}
