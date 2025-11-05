import { Container, Heading, Stack, Text } from '@/ui';
import NewsFeed from '@/components/news/NewsFeed';

export default function NewsPage() {
  return (
    <Container size="lg" pt="xl" pb="xl">
      <Stack gap="sm" mb="xl">
        <Heading order={2}>Actualités de marché</Heading>
        <Text c="dimmed">Flux temps réel scoré par pertinence et impact.</Text>
      </Stack>
      <NewsFeed />
    </Container>
  );
}
