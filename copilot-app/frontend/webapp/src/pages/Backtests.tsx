import { Stack, Title, Text } from '@mantine/core';
import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import BacktestsPanelEnhanced from '@/components/widgets/BacktestsPanelEnhanced';

export default function BacktestsPage() {
  const [params] = useSearchParams();

  const query = useMemo(() => ({
    strategy: params.get('strategy') ?? 'long_top_score',
    universe: params.get('universe') ?? undefined,
    benchmark: params.get('benchmark') ?? undefined,
    horizon: params.get('horizon') ?? undefined,
  }), [params]);

  return (
    <Stack gap="lg">
      <div>
        <Title order={2}>Backtests</Title>
        <Text c="dimmed" mt={4}>
          Performance historique des stratégies Finance Copilot. Branchez une stratégie backend réelle — données sans mock.
        </Text>
      </div>
      <BacktestsPanelEnhanced
        strategy={query.strategy}
        universe={query.universe}
        benchmark={query.benchmark}
        horizon={query.horizon}
      />
    </Stack>
  );
}
