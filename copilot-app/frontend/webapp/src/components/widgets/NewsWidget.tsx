/**
 * News Widget for Dashboard
 * Displays latest financial news articles with improved UI
 */

import { Card, Stack, Title, Text, Badge, Group, ActionIcon, Alert } from '@mantine/core';
import { IconNews, IconExternalLink, IconRefresh } from '@tabler/icons-react';
import { useApi } from '@/hooks/useApi';

interface NewsArticle {
  id: string;
  title: string;
  summary?: string;
  url: string;
  source?: string;
  pubDate?: string;
  tickers?: string[];
  sentiment_score?: number;
}

export function NewsWidget() {
  const { data, isLoading, error, refetch } = useApi<any>('/api/news/feed?limit=5');

  // Process the news data
  let articles: any[] = [];
  if (data && data.articles) {
    articles = data.articles;
  } else if (data && Array.isArray(data)) {
    articles = data;
  } else if (data && data.rows) {
    articles = data.rows; // Different API structure
  } else if (data && data.data) {
    // Nested structure
    if (data.data.articles) articles = data.data.articles;
    else if (Array.isArray(data.data)) articles = data.data;
  }

  return (
    <Card padding="lg" shadow="sm" withBorder>
      <Stack gap="md">
        <Group justify="space-between">
          <Group gap="xs">
            <IconNews size={24} color="#3B82F6" />
            <Title order={4}>Market News</Title>
          </Group>
          <ActionIcon 
            size="sm" 
            variant="light" 
            color="blue" 
            onClick={() => refetch()} 
            loading={isLoading}
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </Group>

        {isLoading && (
          <Stack gap="sm">
            {[...Array(3)].map((_, i) => (
              <Card key={i} withBorder padding="sm">
                <Stack gap="xs">
                  <Text fw={600} size="sm">
                    <Text size="sm" style={{ display: 'inline-block', width: '70%', height: '16px', backgroundColor: '#e2e8f0', borderRadius: '4px' }}>&nbsp;</Text>
                  </Text>
                  <Group gap="xs">
                    <Text size="sm" style={{ display: 'inline-block', width: '30%', height: '12px', backgroundColor: '#e2e8f0', borderRadius: '4px' }}>&nbsp;</Text>
                  </Group>
                  <Text size="xs" c="dimmed">
                    <Text size="xs" style={{ display: 'inline-block', width: '60%', height: '12px', backgroundColor: '#e2e8f0', borderRadius: '4px' }}>&nbsp;</Text>
                  </Text>
                </Stack>
              </Card>
            ))}
          </Stack>
        )}

        {error && (
          <Alert color="red" variant="light" title="Data Error">
            <Text size="sm">Failed to load news: {error}</Text>
          </Alert>
        )}

        {!isLoading && !error && articles.length > 0 && (
          <Stack gap="sm">
            {articles.map((article: any, index: number) => {
              // Handle various possible field names for articles
              const id = article.id || `news-${index}`;
              const title = article.title || article.headline || 'Untitled Article';
              const url = article.url || article.link || article.href || '#';
              const source = article.source || article.publisher || article.sourceDomain || 'Unknown Source';
              const description = article.summary || article.description || article.excerpt || '';
              const tickers = article.tickers || article.symbols || [];
              const pubDate = article.pubDate || article.published_at || article.date || article.createdAt;
              
              return (
                <Card key={id} withBorder padding="sm" radius="md">
                  <Stack gap="xs">
                    <Group justify="space-between" align="flex-start">
                      <Text fw={600} size="sm" lineClamp={2} style={{ flex: 1 }}>
                        {title}
                      </Text>
                      <a 
                        href={url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ textDecoration: 'none', color: 'inherit' }}
                      >
                        <ActionIcon size="sm" variant="subtle" color="blue">
                          <IconExternalLink size={14} />
                        </ActionIcon>
                      </a>
                    </Group>

                    <Group gap="xs" wrap="wrap">
                      {source && (
                        <Badge size="xs" variant="light" color="blue">
                          {source.toUpperCase()}
                        </Badge>
                      )}
                      
                      {tickers && Array.isArray(tickers) && tickers.length > 0 && tickers.slice(0, 3).map((ticker: string, idx: number) => (
                        <Badge key={idx} size="xs" variant="light" color="indigo">
                          {ticker}
                        </Badge>
                      ))}
                      
                      {pubDate && (
                        <Text size="xs" c="dimmed">
                          {new Date(pubDate).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric'
                          })}
                        </Text>
                      )}
                    </Group>

                    {description && (
                      <Text size="xs" c="dimmed" lineClamp={2}>
                        {description}
                      </Text>
                    )}
                  </Stack>
                </Card>
              );
            })}
          </Stack>
        )}

        {!isLoading && !error && articles.length === 0 && (
          <Text size="sm" c="dimmed" ta="center">
            No recent news available
          </Text>
        )}
      </Stack>
    </Card>
  );
}
