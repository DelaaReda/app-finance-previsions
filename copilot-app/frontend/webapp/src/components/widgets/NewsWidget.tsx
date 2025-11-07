/**
 * Simple News Widget for Dashboard
 * Displays latest news articles
 */

import { Card, Stack, Title, Text, Badge, Group, Button, Anchor } from '@mantine/core';
import { IconNews, IconExternalLink } from '@tabler/icons-react';
import { useNews } from '@/hooks/useNews';

type Props = {
  universe?: string[];
  limit?: number;
};

export function NewsWidget({ universe = ['SPY', 'QQQ', 'AAPL'], limit = 5 }: Props) {
  const { data: articles, isLoading, error, refetch } = useNews({ universe, limit });

  return (
    <Card padding="lg">
      <Stack gap="md">
        <Group justify="space-between">
          <Group gap="xs">
            <IconNews size={24} color="#4169E1" />
            <Title order={4}>Latest News</Title>
          </Group>
          <Button size="xs" variant="light" onClick={() => refetch()}>
            Refresh
          </Button>
        </Group>

        {isLoading && <Text c="dimmed">Loading news...</Text>}
        {error && <Text c="red">Error loading news</Text>}

        {!isLoading && !error && articles && articles.length > 0 && (
          <Stack gap="sm">
            {articles.slice(0, limit).map((article) => (
              <Card key={article.id} withBorder padding="sm">
                <Stack gap="xs">
                  <Group justify="space-between" align="flex-start">
                    <Text fw={600} size="sm" lineClamp={2} style={{ flex: 1 }}>
                      {article.title}
                    </Text>
                    <Anchor href={article.link || article.url} target="_blank" rel="noopener">
                      <IconExternalLink size={16} />
                    </Anchor>
                  </Group>

                  <Group gap="xs">
                    {article.source && (
                      <Badge size="xs" variant="light">{article.source}</Badge>
                    )}
                    {article.pubDate && (
                      <Text size="xs" c="dimmed">
                        {new Date(article.pubDate).toLocaleString()}
                      </Text>
                    )}
                  </Group>

                  {article.description && (
                    <Text size="xs" c="dimmed" lineClamp={2}>
                      {article.description}
                    </Text>
                  )}
                </Stack>
              </Card>
            ))}
          </Stack>
        )}

        {!isLoading && !error && (!articles || articles.length === 0) && (
          <Text c="dimmed" ta="center">No news available</Text>
        )}
      </Stack>
    </Card>
  );
}
