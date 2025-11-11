/**
 * News Widget for Dashboard
 * Displays latest financial news articles with improved UI
 */

import { Card, Stack, Title, Text, Badge, Group, ActionIcon, Skeleton, Button } from '@mantine/core';
import { IconNews, IconExternalLink, IconRefresh } from '@tabler/icons-react';
import { useApi } from '@/hooks/useApi';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import styles from './NewsWidget.module.css';
import ErrorAlert from '@/components/ui/ErrorAlert';
import { NewsCard } from '@/features/okc/components/desktop/NewsCard';

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
          <ErrorAlert
            title="Erreur de chargement"
            message="Impossible de charger les actualités."
            error={error}
            onReload={() => refetch()}
          />
        )}

        {!isLoading && !error && articles.length > 0 && (
          <Stack gap="sm" className={styles.newsList}>
            {articles.map((article: any, index: number) => {
              const id = article.id || `news-${index}`;
              const title = article.title || article.headline || 'Untitled Article';
              const url = article.url || article.link || article.href || '#';
              const source = article.source || article.publisher || article.sourceDomain || 'Unknown Source';
              const pubDate = article.pubDate || article.published_at || article.date || article.createdAt;
              const time = pubDate ? new Date(pubDate).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }) : undefined;
              return <NewsCard key={id} title={title} source={source} url={url} time={time} />;
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
