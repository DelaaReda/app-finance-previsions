/**
 * News Widget for Dashboard
 * Displays latest financial news articles with improved UI
 */

import { Card, Stack, Title, Text, Badge, Group, ActionIcon, Alert, Skeleton, Anchor, Button } from '@mantine/core';
import { IconNews, IconExternalLink, IconRefresh } from '@tabler/icons-react';
import { useApi } from '@/hooks/useApi';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import styles from './NewsWidget.module.css';

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
    <Card padding="lg" radius="xl" className={`${sharedStyles.glassCard} ${styles.widgetCard}`}>
      <Stack gap="md">
        <Group justify="space-between">
          <Group gap="xs" align="center">
            <div className={`${sharedStyles.sparkIcon} ${styles.newsIcon}`}>
              <IconNews size={18} />
            </div>
            <Title order={4}>Actualités de marché</Title>
          </Group>
          <ActionIcon 
            size="sm" 
            variant="light" 
            color="blue" 
            onClick={() => refetch()} 
            loading={isLoading}
            className={sharedStyles.actionIcon}
            aria-label="Actualiser les actualités"
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </Group>

        {isLoading && (
          <Stack gap="sm">
            {[...Array(3)].map((_, i) => (
              <div key={i} className={`${sharedStyles.skeletonCard} ${styles.newsSkeleton}`}>
                <Skeleton height={16} width="70%" radius="xl" />
                <Skeleton height={12} width="40%" radius="xl" />
                <Skeleton height={12} width="60%" radius="xl" />
              </div>
            ))}
          </Stack>
        )}

        {error && (
          <Alert 
            color="red" 
            variant="light" 
            title="Erreur de chargement"
            action={
              <Button 
                size="xs" 
                variant="light" 
                onClick={() => refetch()}
                aria-label="Réessayer de charger les actualités"
              >
                Réessayer
              </Button>
            }
          >
            <Text size="sm">Impossible de charger les actualités: {String(error)}</Text>
          </Alert>
        )}

        {!isLoading && !error && articles.length > 0 && (
          <Stack gap="sm" className={styles.newsList}>
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
                <div key={id} className={`${sharedStyles.flatCard} ${styles.newsCard}`}>
                  <Group justify="space-between" align="flex-start" wrap="nowrap">
                    <Stack gap={4} className={styles.newsBody} style={{ flex: 1, minWidth: 0 }}>
                      <Anchor
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        underline="hover"
                        style={{ 
                          textDecoration: 'none',
                          color: 'inherit'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.textDecoration = 'underline';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.textDecoration = 'none';
                        }}
                      >
                        <Text 
                          fw={600} 
                          size="sm" 
                          lineClamp={2}
                          style={{ 
                            cursor: 'pointer',
                            transition: 'color 0.2s'
                          }}
                        >
                          {title}
                        </Text>
                      </Anchor>
                      <Group gap="xs" wrap="wrap">
                        {source && (
                          <Badge 
                            size="xs" 
                            variant="light" 
                            color="blue"
                            component="a"
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ cursor: 'pointer' }}
                          >
                            {source.toUpperCase()}
                          </Badge>
                        )}
                        {tickers && Array.isArray(tickers) && tickers.length > 0 && tickers.slice(0, 3).map((ticker: string, idx: number) => (
                          <Badge key={idx} size="xs" variant="dot" color="indigo">
                            {ticker}
                          </Badge>
                        ))}
                      </Group>
                      {description && (
                        <Text size="xs" c="dimmed" lineClamp={2}>
                          {description}
                        </Text>
                      )}
                      {pubDate && (
                        <Text size="xs" c="dimmed">
                          {new Date(pubDate).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })} • {new Date(pubDate).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}
                        </Text>
                      )}
                    </Stack>
                    <ActionIcon
                      component="a"
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      variant="light"
                      color="blue"
                      size="sm"
                      title="Ouvrir l'article"
                    >
                      <IconExternalLink size={16} />
                    </ActionIcon>
                  </Group>
                </div>
              );
            })}
          </Stack>
        )}

        {!isLoading && !error && articles.length === 0 && (
          <Alert 
            color="blue" 
            variant="light"
            title="Aucune actualité récente"
            action={
              <Button size="xs" variant="light" onClick={() => refetch()}>
                Actualiser
              </Button>
            }
          >
            <Text size="sm">Aucune actualité disponible pour le moment.</Text>
            <Text size="xs" c="dimmed" mt="xs">
              Le système récupère les actualités en arrière-plan. Réessayez dans quelques instants.
            </Text>
          </Alert>
        )}
      </Stack>
    </Card>
  );
}
