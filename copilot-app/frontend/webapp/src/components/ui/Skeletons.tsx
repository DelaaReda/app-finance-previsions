/**
 * Skeletons réutilisables pour loading states
 * Design professionnel avec Mantine
 */

import { Skeleton, Stack, SimpleGrid, Card } from '@mantine/core';

/**
 * Skeleton pour page de prévisions
 */
export function ForecastsSkeleton() {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing="lg">
      {[...Array(12)].map((_, i) => (
        <Card key={i} padding="lg" radius="md" withBorder>
          <Stack gap="sm">
            <Skeleton height={24} width="60%" />
            <Skeleton height={16} width="80%" />
            <Stack gap="xs" mt="md">
              <Skeleton height={20} width="40%" />
              <Skeleton height={32} width="50%" />
            </Stack>
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}

/**
 * Skeleton pour Market Brief
 */
export function BriefSkeleton() {
  return (
    <Stack gap="xl">
      <Card padding="lg" radius="md" withBorder>
        <Stack gap="md">
          <Skeleton height={32} width="40%" />
          <Skeleton height={20} width="60%" />
          <Skeleton height={16} width="80%" />
        </Stack>
      </Card>
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <Card padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Skeleton height={24} width="50%" />
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} height={60} />
            ))}
          </Stack>
        </Card>
        <Card padding="lg" radius="md" withBorder>
          <Stack gap="md">
            <Skeleton height={24} width="50%" />
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} height={60} />
            ))}
          </Stack>
        </Card>
      </SimpleGrid>
    </Stack>
  );
}

/**
 * Skeleton pour tableau de données
 */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Stack gap="xs">
      <Skeleton height={40} /> {/* Header */}
      {[...Array(rows)].map((_, i) => (
        <Skeleton key={i} height={48} />
      ))}
    </Stack>
  );
}

/**
 * Skeleton pour cards de métriques
 */
export function MetricsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, md: count }} spacing="lg">
      {[...Array(count)].map((_, i) => (
        <Card key={i} padding="lg" radius="md" withBorder>
          <Stack gap="sm">
            <Skeleton height={16} width="60%" />
            <Skeleton height={32} width="40%" />
            <Skeleton height={12} width="80%" />
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}

/**
 * Skeleton pour graphique
 */
export function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Skeleton height={24} width="40%" />
        <Skeleton height={height} />
      </Stack>
    </Card>
  );
}

