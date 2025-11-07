import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { stocksService } from '@/services/stocks.service';
import { AreaChart, BarList, Card, Heading, RingProgress, SimpleGrid, Stack, Text, Button, Group, Text as MantineText, TextInput } from '@/ui';
import { IconTrendingDown, IconTrendingUp } from '@tabler/icons-react';
import { StocksScreenerWidget } from '@/components/widgets/StocksScreenerWidget';

const formatPriceSeries = (raw?: any) => {
  if (!raw || !raw.data?.tickers) return [];
  const tickerKey = Object.keys(raw.data.tickers)[0];
  const series = raw.data.tickers[tickerKey];
  if (!series?.points) return [];
  return series.points.map(([ts, price]: [number, number]) => ({
    date: new Date(ts * 1000).toISOString().slice(0, 10),
    price,
  }));
};

export default function Stocks() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL');

  const { data: searchResults } = useQuery({
    queryKey: ['stocks-search', searchQuery],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return [];
      const result = await stocksService.search(searchQuery);
      return result.ok ? result.data : [];
    },
    enabled: searchQuery.length >= 2,
  });

  const { data: analysis } = useQuery({
    queryKey: ['stock-analysis', selectedTicker],
    queryFn: async () => {
      const result = await stocksService.getAnalysis(selectedTicker);
      return result.ok ? result.data : null;
    },
    enabled: !!selectedTicker,
  });

  const { data: priceSeries } = useQuery({
    queryKey: ['stock-prices', selectedTicker],
    queryFn: async () => {
      const result = await stocksService.getPrices(selectedTicker, '1d', 250);
      return result.ok ? result.data : null;
    },
    enabled: !!selectedTicker,
  });

  const chartData = useMemo(() => formatPriceSeries(priceSeries), [priceSeries]);

  const signals = useMemo(() => {
    if (!analysis?.signals) return [];
    return analysis.signals.map((signal: any) => ({
      name: `${signal.type?.toUpperCase?.() ?? 'SIGNAL'} • ${signal.indicator ?? 'Indicateur'}`,
      value: Number(signal.strength ?? 0),
    }));
  }, [analysis]);
  const changePercent = analysis?.stock?.changePercent ?? 0;

  return (
    <Stack gap="xl" data-testid="stocks-screener">
      <StocksScreenerWidget />

      <Heading order={2}>Analyse Actions</Heading>

      <Card>
        <Stack gap="md">
          <Group justify="space-between">
            <Heading order={4}>Recherche de ticker</Heading>
          </Group>
          <Group gap="sm">
            <TextInput
              value={searchQuery}
              placeholder="Ticker ou nom (ex: AAPL, Apple)"
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
              radius="md"
              style={{ flex: 1 }}
            />
            <Button onClick={() => searchResults && searchResults[0] && setSelectedTicker(searchResults[0].ticker)}>
              Explorer
            </Button>
          </Group>
          {searchResults && searchResults.length > 0 && (
            <Stack gap="xs">
              {searchResults.map((stock: any) => {
                const positive = stock.changePercent >= 0;
                return (
                  <Button
                    key={stock.ticker}
                    variant="light"
                    color={positive ? 'teal' : 'red'}
                    onClick={() => {
                      setSelectedTicker(stock.ticker);
                      setSearchQuery('');
                    }}
                    leftSection={positive ? <IconTrendingUp size={14} /> : <IconTrendingDown size={14} />}
                  >
                    <Group justify="space-between" style={{ width: '100%' }}>
                      <Text fw={600}>{stock.ticker}</Text>
                      <Text c="dimmed" fz="xs">{stock.name}</Text>
                      <Text fw={600}>{positive ? '+' : ''}{stock.changePercent.toFixed(2)}%</Text>
                    </Group>
                  </Button>
                );
              })}
            </Stack>
          )}
        </Stack>
      </Card>

      {analysis && (
        <Stack gap="xl">
          <SimpleGrid cols={{ base: 1, lg: 3 }} spacing="lg">
            <Card>
              <Stack gap="sm">
                <Heading order={4}>{analysis.stock.name}</Heading>
                <Text c="dimmed">{analysis.stock.ticker}</Text>
                <RingProgress
                  size={150}
                  thickness={14}
                  roundCaps
                  sections={[{ value: Math.max(0, Math.min(100, (analysis.score.composite ?? 0))), color: 'indigo' }]}
                  label={<Text fw={700} fz="xl">{Math.round(analysis.score.composite ?? 0)}</Text>}
                />
                <Group gap="sm">
                  <MantineText fw={600} fz="lg">${analysis.stock.price?.toFixed?.(2) ?? '—'}</MantineText>
                  <MantineText c={changePercent >= 0 ? 'teal.5' : 'red.5'}>
                    {changePercent >= 0 ? '+' : ''}{changePercent.toFixed(2)}%
                  </MantineText>
                </Group>
                    <Text c="dimmed" fz="sm">Secteur : {analysis.stock.sector}</Text>
                    <Text c="dimmed" fz="sm">Volume : {((analysis.stock.volume ?? 0) / 1_000_000).toFixed(2)}M</Text>
              </Stack>
            </Card>

            <Card>
              <Stack gap="sm">
                <Heading order={4}>Sentiers techniques</Heading>
                <SimpleGrid cols={2} spacing="md">
                  <Stack gap={0}>
                    <Text c="dimmed" fz="xs">SMA 20</Text>
                    <Text fw={600}>${analysis.technicals.sma20?.toFixed?.(2) ?? '—'}</Text>
                  </Stack>
                  <Stack gap={0}>
                    <Text c="dimmed" fz="xs">SMA 50</Text>
                    <Text fw={600}>${analysis.technicals.sma50?.toFixed?.(2) ?? '—'}</Text>
                  </Stack>
                  <Stack gap={0}>
                    <Text c="dimmed" fz="xs">SMA 200</Text>
                    <Text fw={600}>${analysis.technicals.sma200?.toFixed?.(2) ?? '—'}</Text>
                  </Stack>
                  <Stack gap={0}>
                    <Text c="dimmed" fz="xs">RSI</Text>
                    <Text fw={600}>{analysis.technicals.rsi?.toFixed?.(1) ?? '—'}</Text>
                  </Stack>
                </SimpleGrid>
              </Stack>
            </Card>

            <Card>
              <Stack gap="sm">
                <Heading order={4}>Scores multi-piliers</Heading>
                <BarList
                  data={[
                    { name: 'Macro', value: Number(analysis.score.macro ?? 0) },
                    { name: 'Technique', value: Number(analysis.score.technical ?? 0) },
                    { name: 'News', value: Number(analysis.score.news ?? 0) },
                  ]}
                  color="teal"
                />
                <Text c="dimmed" fz="xs">
                  Composite {Math.round(analysis.score.composite ?? 0)}/100
                </Text>
              </Stack>
            </Card>
          </SimpleGrid>

          <Card>
            <Stack gap="md">
              <Heading order={4}>Courbe des prix (1 an)</Heading>
                <AreaChart
                  data={chartData}
                  index="date"
                  categories={[ 'price' ]}
                  colors={[ 'indigo' ]}
                  valueFormatter={(v) => `$${Number(v).toFixed(2)}`}
                  showLegend={false}
                  yAxisWidth={50}
                />
            </Stack>
          </Card>

          {signals && signals.length > 0 && (
            <Card>
              <Stack gap="md">
                <Heading order={4}>Signaux détectés</Heading>
                <BarList data={signals} color="orange" valueFormatter={(value: number) => `${value.toFixed(0)}`} />
              </Stack>
            </Card>
          )}
        </Stack>
      )}
    </Stack>
  );
}
