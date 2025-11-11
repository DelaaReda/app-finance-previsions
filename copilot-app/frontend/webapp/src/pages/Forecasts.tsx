import { Suspense, lazy } from 'react';
import { Container, Stack, Title, Text, Alert, Skeleton } from '@mantine/core';
import { IconChartLine } from '@tabler/icons-react';
import { ErrorBoundary } from 'react-error-boundary';
import PageHeader from '@/components/layout/PageHeader';

// Lazy load ForecastsProBoard for code splitting (Sprint 5 - Tâche 5.2)
const ForecastsProBoard = lazy(() => 
  import('@/components/widgets/ForecastsProBoard').then(m => ({ default: m.default }))
);

function FallbackComponent() {
  return (
    <Alert icon={<IconChartLine />} title="Fonctionnalité en développement" color="blue">
      <Text size="sm">
        Le module Forecasts Pro est en cours de développement. Les données seront disponibles prochainement.
      </Text>
    </Alert>
  );
}

function ForecastsSkeleton() {
  return (
    <Stack gap="xl">
      <Skeleton height={200} radius="md" />
      <Skeleton height={400} radius="md" />
    </Stack>
  );
}

export default function Forecasts() {
  return (
    <Container size="xl" py="xl" data-testid="forecasts-page">
      <PageHeader
        title="Prévisions de marché"
        icon={<IconChartLine size={28} />}
        description="Analyse temps réel des signaux quantitatifs multi-horizons — données 100% backend"
        badge={{ label: 'ML+LLM', color: 'blue' }}
      />
      <ErrorBoundary FallbackComponent={FallbackComponent}>
        <Suspense fallback={<ForecastsSkeleton />}>
          <ForecastsProBoard />
        </Suspense>
      </ErrorBoundary>
    </Container>
  );
}
