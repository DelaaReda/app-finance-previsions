import { useState } from 'react';
import { 
  Stack, 
  Title, 
  Group, 
  Badge, 
  Card, 
  Text, 
  Button, 
  SegmentedControl,
  Select,
  Grid,
  Alert,
  Loader,
} from '@mantine/core';
import { IconRadar, IconAlertCircle, IconRefresh } from '@tabler/icons-react';
import { NewsTreemap } from '@/components/news/NewsTreemap';
import { SentimentDistribution } from '@/components/news/SentimentDistribution';
import { useNewsSignals, type NewsSignalsFilters } from '@/hooks/useNewsSignals';

/**
 * Default tickers to track (can be extended)
 */
const DEFAULT_TICKERS = [
  // Tech
  'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'TSLA',
  // Finance
  'JPM', 'BAC', 'GS', 'C',
  // Healthcare
  'JNJ', 'PFE', 'UNH',
  // Energy
  'XOM', 'CVX',
  // Consumer
  'AMZN', 'WMT', 'HD', 'MCD',
  // ETFs
  'SPY', 'QQQ', 'TLT', 'GLD',
];

/**
 * NewsSignalRadar Page
 * 
 * Visual treemap/heatmap of news signals by ticker
 */
export default function NewsSignalRadar() {
  // Filters state
  const [filters, setFilters] = useState<NewsSignalsFilters>({
    timeframe: '24h',
    minArticles: 1,
  });

  // Fetch and process news signals
  const { data, isLoading, isError, totalArticles, sentimentDistribution } = useNewsSignals(
    DEFAULT_TICKERS,
    filters
  );

  // Handle filter changes
  const handleSectorChange = (value: string | null) => {
    setFilters((prev) => ({
      ...prev,
      sector: value === 'All' ? undefined : (value || undefined),
    }));
  };

  const handleTimeframeChange = (value: string) => {
    setFilters((prev) => ({
      ...prev,
      timeframe: value as '24h' | '7d' | '30d',
    }));
  };

  const handleRefresh = () => {
    // Force refetch by changing a dummy state or using queryClient.invalidateQueries
    window.location.reload(); // Simple approach for now
  };

  return (
    <Stack gap="xl" p="md">
      {/* Header */}
      <Group justify="space-between" align="flex-start">
        <Stack gap="xs">
          <Group gap="sm">
            <IconRadar size={32} stroke={2} />
            <Title order={1}>News Signal Radar</Title>
            <Badge
              color="red"
              variant="dot"
              size="lg"
              style={{ animation: 'pulse 2s ease-in-out infinite' }}
            >
              Live
            </Badge>
          </Group>
          <Text c="dimmed" size="sm">
            Visual heatmap of market news by ticker - Bloomberg Terminal style
          </Text>
        </Stack>

        <Button
          leftSection={<IconRefresh size={16} />}
          variant="light"
          onClick={handleRefresh}
        >
          Refresh
        </Button>
      </Group>

      {/* Filters */}
      <Card withBorder padding="md">
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <Select
              label="Sector Filter"
              placeholder="Select sector"
              data={[
                { value: 'All', label: 'All Sectors' },
                { value: 'Technology', label: 'Technology' },
                { value: 'Finance', label: 'Finance' },
                { value: 'Healthcare', label: 'Healthcare' },
                { value: 'Energy', label: 'Energy' },
                { value: 'Consumer', label: 'Consumer' },
                { value: 'ETF/Index', label: 'ETF/Index' },
              ]}
              value={filters.sector || 'All'}
              onChange={handleSectorChange}
            />
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <Stack gap="xs">
              <Text size="sm" fw={500}>
                Timeframe
              </Text>
              <SegmentedControl
                value={filters.timeframe || '24h'}
                onChange={handleTimeframeChange}
                data={[
                  { label: 'Today', value: '24h' },
                  { label: 'This Week', value: '7d' },
                  { label: 'This Month', value: '30d' },
                ]}
              />
            </Stack>
          </Grid.Col>

          <Grid.Col span={{ base: 12, sm: 12, md: 4 }}>
            <Stack gap="xs" justify="flex-end" h="100%">
              <Group gap="md">
                <div>
                  <Text size="xs" c="dimmed">
                    Total Articles
                  </Text>
                  <Text size="lg" fw={700}>
                    {totalArticles}
                  </Text>
                </div>
                <div>
                  <Text size="xs" c="dimmed">
                    Tracked Tickers
                  </Text>
                  <Text size="lg" fw={700}>
                    {data.length}
                  </Text>
                </div>
              </Group>
            </Stack>
          </Grid.Col>
        </Grid>
      </Card>

      {/* Loading State */}
      {isLoading && (
        <Card withBorder padding="xl" style={{ textAlign: 'center' }}>
          <Stack gap="md" align="center">
            <Loader size="lg" />
            <Text c="dimmed">Loading news signals...</Text>
          </Stack>
        </Card>
      )}

      {/* Error State */}
      {isError && (
        <Alert
          icon={<IconAlertCircle size={16} />}
          title="Failed to Load News"
          color="red"
          variant="light"
        >
          Unable to fetch news data. Please try again later.
        </Alert>
      )}

      {/* Main Content */}
      {!isLoading && !isError && (
        <>
          {data.length === 0 ? (
            <Card withBorder padding="xl" style={{ textAlign: 'center' }}>
              <Text c="dimmed">No news signals found for the selected filters</Text>
            </Card>
          ) : (
            <Grid>
              {/* Treemap Visualization */}
              <Grid.Col span={12}>
                <Card withBorder padding="lg" radius="md">
                  <Stack gap="md">
                    <Group justify="space-between">
                      <Text size="lg" fw={600}>
                        News Heatmap
                      </Text>
                      <Text size="sm" c="dimmed">
                        Size = article count | Color = sentiment
                      </Text>
                    </Group>
                    <NewsTreemap data={data} />
                  </Stack>
                </Card>
              </Grid.Col>

              {/* Sentiment Distribution */}
              <Grid.Col span={{ base: 12, md: 4 }}>
                <SentimentDistribution
                  distribution={sentimentDistribution}
                  totalArticles={totalArticles}
                />
              </Grid.Col>

              {/* Top News List */}
              <Grid.Col span={{ base: 12, md: 8 }}>
                <Card withBorder padding="lg" radius="md">
                  <Stack gap="md">
                    <Text size="lg" fw={600}>
                      Latest News
                    </Text>
                    <Stack gap="sm">
                      {data
                        .slice(0, 10)
                        .flatMap((signal) =>
                          signal.recentNews.slice(0, 1).map((article) => ({
                            ...article,
                            ticker: signal.ticker,
                            sentiment: signal.sentiment,
                            freshness: signal.freshness,
                          }))
                        )
                        .sort((a, b) => a.freshness - b.freshness)
                        .slice(0, 10)
                        .map((item, idx) => {
                          const emoji =
                            item.sentiment === 'positive'
                              ? '🟢'
                              : item.sentiment === 'negative'
                              ? '🔴'
                              : '🟡';

                          const freshnessColor =
                            item.freshness < 10
                              ? 'green'
                              : item.freshness < 60
                              ? 'yellow'
                              : item.freshness < 240
                              ? 'orange'
                              : 'red';

                          const timeAgo =
                            item.freshness < 1
                              ? 'Just now'
                              : item.freshness < 60
                              ? `${Math.floor(item.freshness)}m ago`
                              : item.freshness < 1440
                              ? `${Math.floor(item.freshness / 60)}h ago`
                              : `${Math.floor(item.freshness / 1440)}d ago`;

                          return (
                            <Card key={idx} withBorder padding="sm" radius="sm">
                              <Group gap="sm" wrap="nowrap">
                                <Text size="xl">{emoji}</Text>
                                <Stack gap={4} style={{ flex: 1 }}>
                                  <Group gap="xs">
                                    <Badge size="sm" variant="light">
                                      {item.ticker}
                                    </Badge>
                                    <Badge size="xs" color={freshnessColor}>
                                      {timeAgo}
                                    </Badge>
                                  </Group>
                                  <Text size="sm" fw={500} lineClamp={2}>
                                    {item.title}
                                  </Text>
                                  {item.source && (
                                    <Text size="xs" c="dimmed">
                                      {item.source}
                                    </Text>
                                  )}
                                </Stack>
                              </Group>
                            </Card>
                          );
                        })}
                    </Stack>
                  </Stack>
                </Card>
              </Grid.Col>
            </Grid>
          )}
        </>
      )}

      {/* Inline styles for pulse animation */}
      <style>
        {`
          @keyframes pulse {
            0%, 100% {
              opacity: 1;
            }
            50% {
              opacity: 0.5;
            }
          }
        `}
      </style>
    </Stack>
  );
}
