import { Stack, Title, Text, Alert, Loader } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { ErrorBoundary } from 'react-error-boundary';
import ForecastsProBoard from '@/components/widgets/ForecastsProBoard';

function FallbackComponent() {
  return (
    <Alert icon={<IconAlertCircle />} title="Fonctionnalité en développement" color="blue">
      <Text size="sm">
        Le module Forecasts Pro est en cours de développement. Les données seront disponibles prochainement.
      </Text>
    </Alert>
  );
}

export default function Forecasts() {
  return (
    <Stack gap="lg">
      <div className="card">
        <Title order={2}>Prévisions de marché</Title>
        <Text c="dimmed" mt={4}>
          Analyse temps réel des signaux quantitatifs multi-horizons — données 100% backend.
        </Text>
      </div>
      <ErrorBoundary FallbackComponent={FallbackComponent}>
        <ForecastsProBoard />
      </ErrorBoundary>
    </Stack>
  );
}
