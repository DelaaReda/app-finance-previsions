import { useMemo, useState } from 'react';
import { BarChart, BarList, DonutChart } from '@tremor/react';
import {
  Alert,
  Badge,
  Group,
  MultiSelect,
  NumberInput,
  Pagination,
  ScrollArea,
  SegmentedControl,
  Select,
  Stack,
  TextInput,
} from '@mantine/core';
import { IconDownload, IconRefresh } from '@tabler/icons-react';
import { Card, Title, Button, Text } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import { ensureArray } from '@/lib/safe';
import {
  useStocksScreener,
  type StocksScreenerHorizon,
  type StocksScreenerItem,
  type StocksScreenerSort,
} from '@/hooks/useStocksScreener';

type Props = {
  title?: string;
  initialUniverse?: string[];
  sectorOptions?: string[];
  initialHorizon?: StocksScreenerHorizon;
};

function formatUsd(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '—';
  if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  return value.toLocaleString();
}

function formatPct(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '—';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

function exportCsv(items: StocksScreenerItem[]) {
  if (!items.length) return;
  const header = ['ticker','name','sector','price','change_1d','momentum_30d','score','risk','quality','mcap','pe','div_yield'];
  const lines = [header.join(',')];
  items.forEach((item) => {
    lines.push([
      item.ticker,
      `"${(item.name ?? '').replace(/"/g, '""')}"`,
      item.sector ?? '',
      item.price ?? '',
      item.change_1d ?? '',
      item.momentum_30d ?? '',
      item.score ?? '',
      item.risk ?? '',
      item.quality ?? '',
      item.mcap ?? '',
      item.pe ?? '',
      item.div_yield ?? '',
    ].join(','));
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'stocks_screener.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}

export function StocksScreenerWidget({
  title = '📈 Stocks Screener',
  initialUniverse = ['SPY','QQQ','AAPL','NVDA','MSFT'],
  sectorOptions = [
    'Technology','Financials','Healthcare','Energy','Consumer','Industrials','Utilities','Real Estate','Materials','Communication Services',
  ],
  initialHorizon = 'short',
}: Props) {
  const [tickers, setTickers] = useState<string[]>(initialUniverse);
  const [selectedSectors, setSelectedSectors] = useState<string[]>([]);
  const [horizon, setHorizon] = useState<StocksScreenerHorizon>(initialHorizon);
  const [search, setSearch] = useState('');
  const [minMcap, setMinMcap] = useState<number | ''>('');
  const [maxMcap, setMaxMcap] = useState<number | ''>('');
  const [minPe, setMinPe] = useState<number | ''>('');
  const [maxPe, setMaxPe] = useState<number | ''>('');
  const [sort, setSort] = useState<StocksScreenerSort>('score');
  const [order, setOrder] = useState<'asc'|'desc'>('desc');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const query = useStocksScreener({
    universe: tickers,
    sectors: selectedSectors,
    horizon,
    q: search || undefined,
    min_mcap: minMcap === '' ? undefined : Number(minMcap),
    max_mcap: maxMcap === '' ? undefined : Number(maxMcap),
    min_pe: minPe === '' ? undefined : Number(minPe),
    max_pe: maxPe === '' ? undefined : Number(maxPe),
    sort,
    order,
    page,
    page_size: pageSize,
  });

  const items = ensureArray(query.data?.items);
  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const sectorDistribution = useMemo(() => {
    const counts = new Map<string, number>();
    items.forEach((item) => {
      const key = item.sector ?? '—';
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
  }, [items]);

  const scoreBySector = useMemo(() => {
    const agg = new Map<string, { sum: number; count: number }>();
    items.forEach((item) => {
      if (typeof item.score !== 'number') return;
      const key = item.sector ?? '—';
      const entry = agg.get(key) ?? { sum: 0, count: 0 };
      entry.sum += item.score;
      entry.count += 1;
      agg.set(key, entry);
    });
    return Array.from(agg.entries()).map(([sector, { sum, count }]) => ({
      sector,
      score: count ? Number((sum / count).toFixed(1)) : 0,
    })).sort((a, b) => b.score - a.score);
  }, [items]);

  const topMovers = useMemo(() => {
    const gainers = [...items]
      .filter((item) => typeof item.change_1d === 'number')
      .sort((a, b) => (b.change_1d ?? 0) - (a.change_1d ?? 0))
      .slice(0, 10)
      .map((item) => ({ name: `${item.ticker} • ${item.name ?? ''}`, value: Number((item.change_1d ?? 0).toFixed(2)) }));

    const losers = [...items]
      .filter((item) => typeof item.change_1d === 'number')
      .sort((a, b) => (a.change_1d ?? 0) - (b.change_1d ?? 0))
      .slice(0, 10)
      .map((item) => ({ name: `${item.ticker} • ${item.name ?? ''}`, value: Number((item.change_1d ?? 0).toFixed(2)) }));

    return { gainers, losers };
  }, [items]);

  return (
    <Card data-testid="stocks-screener">
      <Group justify="space-between" align="center" wrap="wrap">
        <div>
          <Title order={4}>{title}</Title>
          <Text c="dimmed" mt={4}>
            Filtres multi-critères, scores, risques, momentum, export CSV — connecté à <code>/stocks/screener</code>.
          </Text>
        </div>
        <Group gap="xs" wrap="nowrap">
          <MultiSelect
            aria-label="Univers"
            data={[...new Set([...tickers, ...initialUniverse])].map((value) => ({ value, label: value }))}
            value={tickers}
            onChange={(next) => { setTickers(next); setPage(1); }}
            searchable
            placeholder="Tickers (SPY,QQQ,...)"
            style={{ minWidth: 260 }}
          />
          <MultiSelect
            aria-label="Secteurs"
            data={sectorOptions.map((value) => ({ value, label: value }))}
            value={selectedSectors}
            onChange={(next) => { setSelectedSectors(next); setPage(1); }}
            searchable
            placeholder="Secteurs"
            style={{ minWidth: 220 }}
          />
          <SegmentedControl
            aria-label="Horizon"
            value={horizon}
            onChange={(value) => { setHorizon(value as StocksScreenerHorizon); setPage(1); }}
            data={[{ label: 'Court', value: 'short' }, { label: 'Moyen', value: 'medium' }, { label: 'Long', value: 'long' }]}
          />
          <TextInput
            aria-label="Recherche"
            placeholder="Recherche (ticker, nom)"
            value={search}
            onChange={(event) => { setSearch(event.currentTarget.value); setPage(1); }}
            style={{ width: 200 }}
          />
          <Button onClick={() => exportCsv(items)} variant="light" leftSection={<IconDownload size={16} />}>
            Export CSV
          </Button>
          <Button onClick={() => query.refetch()} loading={query.isFetching} variant="light" leftSection={<IconRefresh size={16} />}>
            Refresh
          </Button>
          <FreshnessBadge freshness={query.data?.updated_at ?? undefined} />
        </Group>
      </Group>

      <Stack mt="md" gap="md">
        <Group grow align="flex-end">
          <NumberInput label="Min MCAP (USD)" value={minMcap} onChange={setMinMcap} thousandSeparator allowDecimal={false} min={0} />
          <NumberInput label="Max MCAP (USD)" value={maxMcap} onChange={setMaxMcap} thousandSeparator allowDecimal={false} min={0} />
          <NumberInput label="Min P/E" value={minPe} onChange={setMinPe} precision={2} min={0} />
          <NumberInput label="Max P/E" value={maxPe} onChange={setMaxPe} precision={2} min={0} />
          <Select
            label="Tri"
            value={sort}
            onChange={(value) => { setSort((value as StocksScreenerSort) ?? 'score'); setPage(1); }}
            data={[
              { value: 'score',        label: 'Score' },
              { value: 'risk',         label: 'Risque' },
              { value: 'momentum_30d', label: 'Momentum 30j' },
              { value: 'change_1d',    label: 'Variation 1j' },
              { value: 'mcap',         label: 'Capitalisation' },
              { value: 'pe',           label: 'P/E' },
              { value: 'div_yield',    label: 'Dividende %' },
              { value: 'quality',      label: 'Qualité' },
            ]}
          />
          <SegmentedControl
            label="Ordre"
            value={order}
            onChange={(value) => { setOrder(value as 'asc' | 'desc'); setPage(1); }}
            data={[{ label: 'Desc', value: 'desc' }, { label: 'Asc', value: 'asc' }]}
          />
        </Group>

        {query.isLoading && <Alert color="blue" title="Chargement">Analyse en cours…</Alert>}
        {query.error && <Alert color="red" title="Erreur">{String(query.error)}</Alert>}

        {!query.isLoading && !query.error && (
          items.length === 0 ? (
            <Alert color="gray" title="Aucun résultat">Aucun titre pour ces filtres.</Alert>
          ) : (
            <Stack gap="lg">
              <Group grow align="start">
                <Card>
                  <Title order={6}>Répartition par secteur</Title>
                  <DonutChart className="mt-3 h-72" data={sectorDistribution} category="value" index="name" showLegend />
                </Card>
                <Card>
                  <Title order={6}>Score moyen par secteur</Title>
                  <BarChart
                    className="mt-3 h-72"
                    data={scoreBySector}
                    index="sector"
                    categories={['score']}
                    showLegend={false}
                    yAxisWidth={40}
                  />
                </Card>
              </Group>

              <Group grow align="start">
                <Card>
                  <Title order={6}>Top gagnants (variation 1j)</Title>
                  <BarList className="mt-2" data={topMovers.gainers} />
                </Card>
                <Card>
                  <Title order={6}>Top perdants (variation 1j)</Title>
                  <BarList className="mt-2" data={topMovers.losers} />
                </Card>
              </Group>

              <Card>
                <Title order={6}>Résultats ({total.toLocaleString()} titres)</Title>
                <ScrollArea type="hover" h={460}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
                    <thead>
                      <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--mantine-color-dark-5)' }}>
                        <th style={{ padding: '8px' }}>Ticker</th>
                        <th style={{ padding: '8px' }}>Nom</th>
                        <th style={{ padding: '8px' }}>Secteur</th>
                        <th style={{ padding: '8px' }}>Prix</th>
                        <th style={{ padding: '8px' }}>1j</th>
                        <th style={{ padding: '8px' }}>Momentum 30j</th>
                        <th style={{ padding: '8px' }}>Score</th>
                        <th style={{ padding: '8px' }}>Risque</th>
                        <th style={{ padding: '8px' }}>Qualité</th>
                        <th style={{ padding: '8px' }}>MCAP</th>
                        <th style={{ padding: '8px' }}>P/E</th>
                        <th style={{ padding: '8px' }}>Div%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => (
                        <tr key={item.ticker} style={{ borderBottom: '1px solid var(--mantine-color-dark-6)' }}>
                          <td style={{ padding: '8px', fontWeight: 600 }}>
                            <Badge variant="light">{item.ticker}</Badge>
                          </td>
                          <td style={{ padding: '8px' }}>{item.name ?? '—'}</td>
                          <td style={{ padding: '8px' }}>{item.sector ?? '—'}</td>
                          <td style={{ padding: '8px' }}>{item.price != null ? `$${item.price.toFixed(2)}` : '—'}</td>
                          <td style={{ padding: '8px', color: (item.change_1d ?? 0) >= 0 ? 'var(--mantine-color-green-5)' : 'var(--mantine-color-red-5)' }}>
                            {formatPct(item.change_1d)}
                          </td>
                          <td style={{ padding: '8px', color: (item.momentum_30d ?? 0) >= 0 ? 'var(--mantine-color-green-5)' : 'var(--mantine-color-red-5)' }}>
                            {formatPct(item.momentum_30d)}
                          </td>
                          <td style={{ padding: '8px' }}>{item.score ?? '—'}</td>
                          <td style={{ padding: '8px' }}>{item.risk ?? '—'}</td>
                          <td style={{ padding: '8px' }}>{item.quality ?? '—'}</td>
                          <td style={{ padding: '8px' }}>{formatUsd(item.mcap)}</td>
                          <td style={{ padding: '8px' }}>{item.pe ?? '—'}</td>
                          <td style={{ padding: '8px' }}>{item.div_yield != null ? `${item.div_yield.toFixed(2)}%` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </ScrollArea>
                <Group justify="space-between" mt="md">
                  <Text c="dimmed" size="sm">Page {page} / {totalPages} • {total.toLocaleString()} titres</Text>
                  <Pagination total={totalPages} value={page} onChange={setPage} />
                </Group>
              </Card>
            </Stack>
          )
        )}
      </Stack>
    </Card>
  );
}
