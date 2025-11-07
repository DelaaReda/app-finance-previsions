import { Container, Stack } from '@mantine/core';
import { IconNews } from '@tabler/icons-react';
import { NewsRadarWidget } from '@/components/widgets/NewsRadarWidget';
import NewsFeed from '@/components/news/NewsFeed';
import PageHeader from '@/components/layout/PageHeader';

export default function NewsPage() {
  return (
    <Container size="lg" py="xl" data-testid="news-feed">
      <PageHeader
        title="Actualités de marché"
        icon={<IconNews size={28} />}
        description="Flux temps réel scoré par pertinence et impact"
        badge={{ label: 'Live', color: 'green' }}
      />
      <Stack gap="xl">
        <NewsRadarWidget />
        <NewsFeed />
      </Stack>
    </Container>
  );
}
