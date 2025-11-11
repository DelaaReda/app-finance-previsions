import { Card, Text, Badge, Tooltip, Group, Stack, Box } from '@mantine/core';
import type { NewsSignalData } from '@/hooks/useNewsSignals';
import { useDrillDown } from '@/contexts/DrillDownContext';

interface NewsTreemapProps {
  data: NewsSignalData[];
  onTickerClick?: (ticker: string) => void;
}

/**
 * Get color based on sentiment
 */
function getSentimentColor(sentiment: 'positive' | 'neutral' | 'negative'): string {
  switch (sentiment) {
    case 'positive':
      return '#10b981'; // Green
    case 'negative':
      return '#ef4444'; // Red
    case 'neutral':
      return '#fbbf24'; // Yellow
  }
}

/**
 * Get sentiment emoji
 */
function getSentimentEmoji(sentiment: 'positive' | 'neutral' | 'negative'): string {
  switch (sentiment) {
    case 'positive':
      return '🟢';
    case 'negative':
      return '🔴';
    case 'neutral':
      return '🟡';
  }
}

/**
 * Get freshness color based on age (minutes)
 */
function getFreshnessColor(ageMinutes: number): string {
  if (ageMinutes < 10) return 'green'; // Fresh
  if (ageMinutes < 60) return 'yellow'; // Recent
  if (ageMinutes < 240) return 'orange'; // Old
  return 'red'; // Stale
}

/**
 * Format time ago
 */
function formatTimeAgo(ageMinutes: number): string {
  if (ageMinutes < 1) return 'Just now';
  if (ageMinutes < 60) return `${Math.floor(ageMinutes)}m ago`;
  if (ageMinutes < 1440) return `${Math.floor(ageMinutes / 60)}h ago`;
  return `${Math.floor(ageMinutes / 1440)}d ago`;
}

/**
 * Calculate grid span based on count (normalized)
 */
function calculateSpan(count: number, maxCount: number): number {
  // Normalize to 1-6 span (grid cols)
  const normalized = count / maxCount;
  
  if (normalized > 0.7) return 6; // Full width
  if (normalized > 0.5) return 4;
  if (normalized > 0.3) return 3;
  if (normalized > 0.15) return 2;
  return 1;
}

/**
 * Calculate height based on count
 */
function calculateHeight(count: number, maxCount: number): number {
  const normalized = count / maxCount;
  
  if (normalized > 0.7) return 200;
  if (normalized > 0.5) return 150;
  if (normalized > 0.3) return 120;
  return 100;
}

/**
 * NewsTreemap Component - Grid-based visualization simulating treemap
 */
export function NewsTreemap({ data, onTickerClick }: NewsTreemapProps) {
  const { navigateToTicker } = useDrillDown();
  
  if (!data || data.length === 0) {
    return (
      <Card withBorder p="xl" style={{ textAlign: 'center' }}>
        <Text c="dimmed">No news signals available</Text>
      </Card>
    );
  }

  const maxCount = Math.max(...data.map(d => d.count));

  const handleTickerClick = (signal: NewsSignalData) => {
    if (onTickerClick) {
      onTickerClick(signal.ticker);
    } else {
      navigateToTicker(signal.ticker, {
        source: 'news-radar',
        reason: `${signal.count} news articles with ${signal.sentiment} sentiment`,
        additionalData: {
          articleCount: signal.count,
          sentiment: signal.sentiment,
          freshness: signal.freshness,
          sector: signal.sector,
        },
      });
    }
  };

  return (
    <Box
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(6, 1fr)',
        gap: '12px',
        width: '100%',
      }}
    >
      {data.map((signal) => {
        const span = calculateSpan(signal.count, maxCount);
        const height = calculateHeight(signal.count, maxCount);
        const color = getSentimentColor(signal.sentiment);
        const emoji = getSentimentEmoji(signal.sentiment);

        return (
          <Tooltip
            key={signal.ticker}
            label={
              <Stack gap="xs">
                <Text size="sm" fw={700}>
                  {signal.ticker}
                </Text>
                <Text size="xs">
                  {signal.count} article{signal.count > 1 ? 's' : ''}
                </Text>
                <Text size="xs">
                  Sentiment: {emoji} {signal.sentiment} ({(signal.avgSentiment * 100).toFixed(0)}%)
                </Text>
                {signal.sector && (
                  <Text size="xs" c="dimmed">
                    Sector: {signal.sector}
                  </Text>
                )}
                <Badge color={getFreshnessColor(signal.freshness)} size="xs">
                  {formatTimeAgo(signal.freshness)}
                </Badge>
                {signal.recentNews.length > 0 && (
                  <>
                    <Text size="xs" fw={600} mt="xs">
                      Latest:
                    </Text>
                    <Text size="xs" lineClamp={2}>
                      {signal.recentNews[0].title}
                    </Text>
                  </>
                )}
                <Text size="xs" c="blue" mt="xs">
                  Click to view details →
                </Text>
              </Stack>
            }
            multiline
            w={300}
            withArrow
            position="top"
            transitionProps={{ duration: 200 }}
          >
            <Card
              withBorder
              padding="md"
              radius="md"
              style={{
                gridColumn: `span ${span}`,
                height: `${height}px`,
                backgroundColor: color,
                opacity: 0.85,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                position: 'relative',
                overflow: 'hidden',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = '1';
                e.currentTarget.style.transform = 'scale(1.02)';
                e.currentTarget.style.zIndex = '10';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '0.85';
                e.currentTarget.style.transform = 'scale(1)';
                e.currentTarget.style.zIndex = '1';
              }}
              onClick={() => handleTickerClick(signal)}
            >
              <Stack gap="xs" align="center">
                {/* Ticker Symbol */}
                <Text
                  size="xl"
                  fw={900}
                  c="white"
                  style={{
                    textShadow: '2px 2px 4px rgba(0,0,0,0.5)',
                  }}
                >
                  {signal.ticker}
                </Text>

                {/* Sentiment Emoji */}
                <Text size="2rem">{emoji}</Text>

                {/* Article Count */}
                <Group gap="xs">
                  <Text size="sm" c="white" fw={600}>
                    {signal.count} article{signal.count > 1 ? 's' : ''}
                  </Text>
                </Group>

                {/* Freshness Badge (only if fresh) */}
                {signal.freshness < 60 && (
                  <Badge
                    color="dark"
                    size="xs"
                    variant="filled"
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
                    }}
                  >
                    {formatTimeAgo(signal.freshness)}
                  </Badge>
                )}
              </Stack>
            </Card>
          </Tooltip>
        );
      })}
    </Box>
  );
}
