import { useMemo } from 'react';
import { useNewsCompat } from '@/hooks/useNewsCompat';
import { Anchor, BarList, Button, Card, Heading, LoadingSpinner, Select, SimpleGrid, Stack, Text, TextInput, Chip, Group, Badge } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import EmptyState from '@/components/ui/EmptyState';

const SINCE_OPTIONS = [
  { value: '1h', label: 'Dernière heure' },
  { value: '6h', label: '6 heures' },
  { value: '1d', label: '1 jour' },
  { value: '3d', label: '3 jours' },
  { value: '7d', label: '7 jours' },
  { value: '14d', label: '14 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
];

const REGION_OPTIONS = [
  { value: 'all', label: 'Toutes régions' },
  { value: 'US', label: 'États-Unis' },
  { value: 'EU', label: 'Europe' },
  { value: 'CA', label: 'Canada' },
  { value: 'INTL', label: 'International' },
];

const SCORE_OPTIONS = [
  { value: 0.0, label: 'Score ≥ 0.0' },
  { value: 0.3, label: 'Score ≥ 0.3' },
  { value: 0.5, label: 'Score ≥ 0.5' },
  { value: 0.7, label: 'Score ≥ 0.7' },
  { value: 0.9, label: 'Score ≥ 0.9' },
];

export default function NewsFeed() {
  const { items, filters, setFilters, loading, error, hasMore, loadMore, freshness } = useNewsCompat();

  const impactList = useMemo(() =>
    items
      .filter((article) => typeof article.sentiment_score === 'number')
      .slice(0, 8)
      .map((item) => ({
        name: item.title,
        value: Number(item.sentiment_score ?? 0),
      })),
  [items]);

  return (
    <Stack gap="xl">
      <Card>
        <Stack gap="md">
          <Group justify="space-between" align="center">
            <Heading order={4}>Filtres</Heading>
            <FreshnessBadge freshness={freshness ?? undefined} />
          </Group>
          <SimpleGrid cols={{ base: 1, md: 2, lg: 4 }} spacing="md">
            <TextInput
              label="Tickers (virgules)"
              placeholder="AAPL,NVDA"
              value={filters.tickers ?? ''}
              onChange={(e) => setFilters({ ...filters, tickers: e.currentTarget.value })}
            />
            <Select
              label="Fenêtre"
              data={SINCE_OPTIONS}
              value={filters.since ?? '7d'}
              onChange={(value) => setFilters({ ...filters, since: value ?? '7d' })}
            />
            <Select
              label="Région"
              data={REGION_OPTIONS}
              value={filters.region ?? 'all'}
              onChange={(value) => setFilters({ ...filters, region: value ?? 'all' })}
            />
            <Select
              label="Score minimal"
              data={SCORE_OPTIONS.map((opt) => ({ value: String(opt.value), label: opt.label }))}
              value={String(filters.score_min ?? 0)}
              onChange={(value) => setFilters({ ...filters, score_min: Number(value ?? 0) })}
            />
          </SimpleGrid>
        </Stack>
      </Card>

      {loading && items.length === 0 && (
        <Stack align="center">
          <LoadingSpinner />
          <Text c="dimmed">Chargement des actualités…</Text>
        </Stack>
      )}

      {error && <Card><Text c="red">Erreur: {error}</Text></Card>}

      {!loading && items.length === 0 && !error && (
        <EmptyState title="Aucun article" subtitle="Ajustez les filtres ou attendez la prochaine ingestion." />
      )}

          {items.length > 0 && (
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="xl">
              {items.map((item) => (
                <Card key={item.id} radius="lg" shadow="md">
                  <Stack gap="sm">
                    <Group justify="space-between">
                      <Badge color={(item.sentiment_score ?? 0) > 0 ? 'teal' : (item.sentiment_score ?? 0) < 0 ? 'red' : 'slate'}>
                        {item.source?.toUpperCase() ?? 'Source' }
                      </Badge>
                      <Chip size="xs" color="indigo" radius="sm">
                        {new Date((item.pubDate ?? item.timestamp ?? new Date().toISOString())).toLocaleString('fr-FR')}
                      </Chip>
                    </Group>
                <Text fw={600}>{item.title}</Text>
                {item.description && <Text c="dimmed" fz="sm">{item.description}</Text>}
                <Group gap="xs">
                  {(item.tickers ?? []).slice(0, 4).map((ticker: string) => (
                    <Chip key={ticker} size="xs" radius="sm" variant="light">{ticker}</Chip>
                  ))}
                </Group>
                <Anchor href={item.link} target="_blank" rel="noreferrer" fz="xs">
                  Ouvrir la source
                </Anchor>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      )}

      {items.length > 0 && (
        <Card>
          <Stack gap="md">
            <Heading order={4}>Top impacts (score)
            </Heading>
            <BarList
              data={impactList.map((article) => ({ name: article.name, value: article.value }))}
              valueFormatter={(value: number) => value.toFixed(2)}
              color="indigo"
            />
          </Stack>
        </Card>
      )}

      {hasMore && (
        <Group justify="center">
          <Button variant="light" onClick={() => loadMore()} disabled={loading}>
            Charger plus
          </Button>
        </Group>
      )}
    </Stack>
  );
}
