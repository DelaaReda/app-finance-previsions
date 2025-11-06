import { Stack, Title, Text } from '@mantine/core';
import ForecastsProBoard from '@/components/widgets/ForecastsProBoard';

export default function ForecastsPage() {
  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>Prévisions de marché</Title>
        <Text c="dimmed" mt={4}>
          Analyse temps réel des signaux quantitatifs multi-horizons — données 100% backend.
        </Text>
      </div>
      <ForecastsProBoard />
    </Stack>
  );
}
