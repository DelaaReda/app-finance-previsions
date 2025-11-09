import { Suspense, lazy } from 'react';
import { Container, Stack, Skeleton } from '@mantine/core';
import { IconNews } from '@tabler/icons-react';
import PageHeader from '@/components/layout/PageHeader';

// Lazy load news components for code splitting (Sprint 4 - Tâche 4.3)
const NewsRadarWidget = lazy(() => 
  import('@/components/widgets/NewsRadarWidget').then(m => ({ default: m.NewsRadarWidget }))
);
const NewsFeed = lazy(() => 
  import('@/components/news/NewsFeed').then(m => ({ default: m.default }))
);

function NewsSkeleton() {
  return (
    <Stack gap="xl">
      <Skeleton height={200} radius="md" />
      <Skeleton height={400} radius="md" />
    </Stack>
  );
}

export default function NewsPage() {
  return (
    <Container size="lg" py="xl" data-testid="news-feed">
      <PageHeader
        title="Actualités de marché"
        icon={<IconNews size={28} />}
        description="Flux temps réel scoré par pertinence et impact"
        badge={{ label: 'Live', color: 'green' }}
      />
      <Suspense fallback={<NewsSkeleton />}>
        <Stack gap="xl">
          <Suspense fallback={<Skeleton height={200} radius="md" />}>
            <NewsRadarWidget />
          </Suspense>
          <Suspense fallback={<Skeleton height={400} radius="md" />}>
            <NewsFeed />
          </Suspense>
        </Stack>
      </Suspense>
    </Container>
  );
}
