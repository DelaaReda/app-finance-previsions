import { Stack, Title, Text } from '@mantine/core';
import HealthBar from '@/components/widgets/HealthBar';
import ForecastsProBoard from '@/components/widgets/ForecastsProBoard';
import BacktestsPanel from '@/components/widgets/BacktestsPanel';
import IntelligenceDashboardWidget from '@/components/widgets/IntelligenceDashboardWidget';

export default function Dashboard() {
  return (
    <Stack data-testid="dashboard-root" gap="lg">
      <div>
        <Title order={2}>Dashboard - Vue d'ensemble</Title>
        <Text c="dimmed" mt={4}>
          Vue opérationnelle : santé des pipelines, prévisions live, performance backtests et intelligence LLM.
        </Text>
      </div>

      <HealthBar />
      <IntelligenceDashboardWidget />
      <ForecastsProBoard />
      <BacktestsPanel strategy="long_top_score" universe="SP500" benchmark="SPY" horizon="short" />
    </Stack>
  );
}
