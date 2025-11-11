import { Card, Text, Group, Progress, Stack, Badge } from '@mantine/core';

interface SentimentDistributionProps {
  distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  totalArticles: number;
}

/**
 * SentimentDistribution Component
 * 
 * Displays sentiment distribution with progress bars and percentages
 */
export function SentimentDistribution({ distribution, totalArticles }: SentimentDistributionProps) {
  // Calculate percentages
  const positivePercent = totalArticles > 0 ? (distribution.positive / totalArticles) * 100 : 0;
  const neutralPercent = totalArticles > 0 ? (distribution.neutral / totalArticles) * 100 : 0;
  const negativePercent = totalArticles > 0 ? (distribution.negative / totalArticles) * 100 : 0;

  // Determine dominant sentiment
  const getDominantSentiment = () => {
    const max = Math.max(distribution.positive, distribution.neutral, distribution.negative);
    if (max === distribution.positive) return 'Positive';
    if (max === distribution.negative) return 'Negative';
    return 'Neutral';
  };

  const dominantSentiment = getDominantSentiment();

  return (
    <Card withBorder padding="lg" radius="md">
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between">
          <Text size="lg" fw={600}>
            Sentiment Distribution
          </Text>
          <Badge
            color={
              dominantSentiment === 'Positive'
                ? 'green'
                : dominantSentiment === 'Negative'
                ? 'red'
                : 'yellow'
            }
            variant="light"
            size="lg"
          >
            {dominantSentiment} Market
          </Badge>
        </Group>

        {/* Positive */}
        <Stack gap={4}>
          <Group justify="space-between">
            <Group gap="xs">
              <Text size="sm" fw={500}>
                🟢 Positive
              </Text>
              <Text size="xs" c="dimmed">
                ({distribution.positive} articles)
              </Text>
            </Group>
            <Text size="sm" fw={600} c="green">
              {positivePercent.toFixed(1)}%
            </Text>
          </Group>
          <Progress value={positivePercent} color="green" size="lg" radius="xl" />
        </Stack>

        {/* Neutral */}
        <Stack gap={4}>
          <Group justify="space-between">
            <Group gap="xs">
              <Text size="sm" fw={500}>
                🟡 Neutral
              </Text>
              <Text size="xs" c="dimmed">
                ({distribution.neutral} articles)
              </Text>
            </Group>
            <Text size="sm" fw={600} c="yellow">
              {neutralPercent.toFixed(1)}%
            </Text>
          </Group>
          <Progress value={neutralPercent} color="yellow" size="lg" radius="xl" />
        </Stack>

        {/* Negative */}
        <Stack gap={4}>
          <Group justify="space-between">
            <Group gap="xs">
              <Text size="sm" fw={500}>
                🔴 Negative
              </Text>
              <Text size="xs" c="dimmed">
                ({distribution.negative} articles)
              </Text>
            </Group>
            <Text size="sm" fw={600} c="red">
              {negativePercent.toFixed(1)}%
            </Text>
          </Group>
          <Progress value={negativePercent} color="red" size="lg" radius="xl" />
        </Stack>

        {/* Total */}
        <Group justify="space-between" pt="xs" style={{ borderTop: '1px solid #e0e0e0' }}>
          <Text size="sm" c="dimmed">
            Total Articles
          </Text>
          <Text size="sm" fw={700}>
            {totalArticles}
          </Text>
        </Group>
      </Stack>
    </Card>
  );
}
