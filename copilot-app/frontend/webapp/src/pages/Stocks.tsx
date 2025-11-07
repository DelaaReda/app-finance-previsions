import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Container, Stack, Group, TextInput, Button, Card, SimpleGrid, Skeleton, Tabs } from '@mantine/core';
import { IconTrendingDown, IconTrendingUp, IconChartLine, IconTarget, IconActivity, IconGauge, IconRadar } from '@tabler/icons-react';
import { stocksService } from '@/services/stocks.service';
import { AreaChart, BarList, Heading, RingProgress, Text, Text as MantineText } from '@/ui';
import { StocksScreenerWidget } from '@/components/widgets/StocksScreenerWidget';
import PageHeader from '@/components/layout/PageHeader';
import { MetricsSkeleton } from '@/components/ui/Skeletons';
import EmptyState from '@/components/ui/EmptyState';
import { StatsGrid, ProgressRing, ComparisonChart, PerformanceGauge, RadarChart, RiskMatrix } from '@/components/visualizations';

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

  const isLoading = !analysis && selectedTicker;

  return (
    <Container size="xl" py="xl" data-testid="stocks-screener">
      <PageHeader
        title="Analyse Actions"
        icon={<IconChartLine size={28} />}
        description="Screener, analyse technique et signaux pour chaque ticker"
        stats={analysis ? [
          { label: 'Score', value: `${Math.round(analysis.score.composite ?? 0)}/100` },
          { label: 'Prix', value: `$${analysis.stock.price?.toFixed(2) ?? '—'}` },
        ] : undefined}
      />

      <Stack gap="xl" mt="xl">
        <StocksScreenerWidget />

        <Card padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Heading order={4}>Recherche de ticker</Heading>
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
              <Stack gap="xs" mt="md">
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

        {isLoading ? (
          <MetricsSkeleton count={4} />
        ) : !analysis ? (
          <EmptyState
            icon={<IconChartLine size={48} />}
            title="Sélectionnez un ticker"
            description="Recherchez un ticker pour voir son analyse complète"
          />
        ) : (
          <Stack gap="xl">
            {/* Métriques visuelles principales */}
            <StatsGrid
              metrics={[
                {
                  label: 'Score Composite',
                  value: `${Math.round(analysis.score.composite ?? 0)}/100`,
                  icon: <IconTarget size={20} />,
                  color: (analysis.score.composite ?? 0) > 70 ? 'teal' : (analysis.score.composite ?? 0) > 50 ? 'orange' : 'red',
                  description: 'Score global multi-piliers',
                },
                {
                  label: 'Prix',
                  value: `$${analysis.stock.price?.toFixed?.(2) ?? '—'}`,
                  change: changePercent,
                  icon: changePercent >= 0 ? <IconTrendingUp size={20} /> : <IconTrendingDown size={20} />,
                  color: changePercent >= 0 ? 'teal' : 'red',
                  description: `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}% aujourd'hui`,
                },
                {
                  label: 'RSI',
                  value: `${analysis.technicals.rsi?.toFixed?.(1) ?? '—'}`,
                  icon: <IconActivity size={20} />,
                  color: (analysis.technicals.rsi ?? 50) > 70 ? 'red' : (analysis.technicals.rsi ?? 50) < 30 ? 'teal' : 'blue',
                  description: 'Relative Strength Index',
                },
                {
                  label: 'Volume',
                  value: `${((analysis.stock.volume ?? 0) / 1_000_000).toFixed(2)}M`,
                  icon: <IconActivity size={20} />,
                  color: 'blue',
                  description: 'Volume échangé',
                },
              ]}
            />

            {/* Rings de scores */}
            <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
              <ProgressRing
                label="Score Composite"
                value={analysis.score.composite ?? 0}
                color={(analysis.score.composite ?? 0) > 70 ? 'teal' : (analysis.score.composite ?? 0) > 50 ? 'orange' : 'red'}
                subtitle={`${analysis.stock.name}`}
                badge={{
                  label: (analysis.score.composite ?? 0) > 70 ? 'Élevé' : (analysis.score.composite ?? 0) > 50 ? 'Moyen' : 'Faible',
                  color: (analysis.score.composite ?? 0) > 70 ? 'teal' : (analysis.score.composite ?? 0) > 50 ? 'orange' : 'red',
                }}
                icon={<IconTarget size={16} />}
                size={120}
              />
              <ProgressRing
                label="Score Macro"
                value={analysis.score.macro ?? 0}
                color="blue"
                subtitle="Alignement macro"
                icon={<IconChartLine size={16} />}
                size={120}
              />
              <ProgressRing
                label="Score Technique"
                value={analysis.score.technical ?? 0}
                color="indigo"
                subtitle="Indicateurs techniques"
                icon={<IconActivity size={16} />}
                size={120}
              />
              <ProgressRing
                label="Score News"
                value={analysis.score.news ?? 0}
                color="orange"
                subtitle="Sentiment actualités"
                icon={<IconTrendingUp size={16} />}
                size={120}
              />
            </SimpleGrid>

            {/* Indicateurs techniques visuels */}
            <Card padding="lg" radius="md" withBorder>
              <Stack gap="md">
                <Heading order={4}>Indicateurs Techniques</Heading>
                <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="lg">
                  <div>
                    <Text c="dimmed" size="xs" mb={4}>SMA 20</Text>
                    <Text fw={700} size="lg">${analysis.technicals.sma20?.toFixed?.(2) ?? '—'}</Text>
                  </div>
                  <div>
                    <Text c="dimmed" size="xs" mb={4}>SMA 50</Text>
                    <Text fw={700} size="lg">${analysis.technicals.sma50?.toFixed?.(2) ?? '—'}</Text>
                  </div>
                  <div>
                    <Text c="dimmed" size="xs" mb={4}>SMA 200</Text>
                    <Text fw={700} size="lg">${analysis.technicals.sma200?.toFixed?.(2) ?? '—'}</Text>
                  </div>
                  <div>
                    <Text c="dimmed" size="xs" mb={4}>RSI</Text>
                    <Text fw={700} size="lg" c={(analysis.technicals.rsi ?? 50) > 70 ? 'red' : (analysis.technicals.rsi ?? 50) < 30 ? 'teal' : undefined}>
                      {analysis.technicals.rsi?.toFixed?.(1) ?? '—'}
                    </Text>
                  </div>
                </SimpleGrid>
              </Stack>
            </Card>

            {/* Graphique de prix */}
            {chartData.length > 0 && (
              <ComparisonChart
                title={`Courbe des prix - ${analysis.stock.ticker}`}
                description="Évolution sur 1 an"
                data={chartData}
                index="date"
                categories={['price']}
                colors={[changePercent >= 0 ? 'teal' : 'red']}
                type="area"
                height={300}
              />
            )}

            {/* Signaux détectés */}
            {signals && signals.length > 0 && (
              <Card padding="lg" radius="md" withBorder>
                <Stack gap="md">
                  <Heading order={4}>Signaux détectés</Heading>
                  <BarList data={signals} color="orange" valueFormatter={(value: number) => `${value.toFixed(0)}`} />
                </Stack>
              </Card>
            )}

            {/* Visualisations avancées */}
            <Tabs defaultValue="gauge" mt="xl">
              <Tabs.List>
                <Tabs.Tab value="gauge" leftSection={<IconGauge size={16} />}>
                  Performance Gauge
                </Tabs.Tab>
                <Tabs.Tab value="radar" leftSection={<IconRadar size={16} />}>
                  Scores Radar
                </Tabs.Tab>
              </Tabs.List>

              <Tabs.Panel value="gauge" pt="xl">
                <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
                  <PerformanceGauge
                    label="Score Composite"
                    value={analysis.score.composite ?? 0}
                    min={0}
                    max={100}
                    thresholds={[
                      { value: 0, color: 'red', label: 'Faible' },
                      { value: 50, color: 'orange', label: 'Moyen' },
                      { value: 75, color: 'teal', label: 'Élevé' },
                    ]}
                    icon={<IconTarget size={20} />}
                    subtitle={`${analysis.stock.ticker} - ${analysis.stock.name}`}
                  />
                  <PerformanceGauge
                    label="Score Technique"
                    value={analysis.score.technical ?? 0}
                    min={0}
                    max={100}
                    thresholds={[
                      { value: 0, color: 'red', label: 'Faible' },
                      { value: 50, color: 'orange', label: 'Moyen' },
                      { value: 75, color: 'teal', label: 'Élevé' },
                    ]}
                    icon={<IconActivity size={20} />}
                    subtitle="Indicateurs techniques"
                  />
                  <PerformanceGauge
                    label="RSI"
                    value={analysis.technicals.rsi ?? 50}
                    min={0}
                    max={100}
                    thresholds={[
                      { value: 0, color: 'teal', label: 'Oversold' },
                      { value: 30, color: 'blue', label: 'Neutre' },
                      { value: 70, color: 'red', label: 'Overbought' },
                    ]}
                    icon={<IconChartLine size={20} />}
                    subtitle="Relative Strength Index"
                  />
                  <PerformanceGauge
                    label="Rendement"
                    value={changePercent + 50}
                    min={0}
                    max={100}
                    thresholds={[
                      { value: 0, color: 'red', label: 'Négatif' },
                      { value: 50, color: 'orange', label: 'Neutre' },
                      { value: 75, color: 'teal', label: 'Positif' },
                    ]}
                    icon={changePercent >= 0 ? <IconTrendingUp size={20} /> : <IconTrendingDown size={20} />}
                    subtitle={`${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`}
                  />
                </SimpleGrid>
              </Tabs.Panel>

              <Tabs.Panel value="radar" pt="xl">
                <RadarChart
                  title={`Scores Multi-Dimensionnels - ${analysis.stock.ticker}`}
                  description="Analyse complète sur 4 dimensions"
                  data={[{
                    dimension: analysis.stock.ticker,
                    Macro: analysis.score.macro ?? 0,
                    Technique: analysis.score.technical ?? 0,
                    News: analysis.score.news ?? 0,
                    Composite: analysis.score.composite ?? 0,
                  }]}
                  index="dimension"
                  categories={['Macro', 'Technique', 'News', 'Composite']}
                  colors={['blue', 'indigo', 'orange', 'teal']}
                />
              </Tabs.Panel>
            </Tabs>
          </Stack>
        )}
      </Stack>
    </Container>
  );
}
