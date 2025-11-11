import { Alert, Badge, Group, SimpleGrid } from '@mantine/core';
import { AreaChart, BarChart } from '@tremor/react';
import { Card, Title } from '@/ui';
import { useBacktests } from '@/hooks/useBacktests';

type Props = {
  strategy: string;
  universe?: string;
  benchmark?: string;
  horizon?: string;
};

export default function BacktestsPanel({ strategy, universe, benchmark, horizon }: Props) {
  const { data, isLoading, error } = useBacktests({ strategy, universe, benchmark, horizon });

  return (
    <Card data-testid="backtests-panel">
      <Group justify="space-between" wrap="wrap">
        <Title order={4}>📚 Backtests — {strategy}</Title>
      </Group>

      {isLoading && <Alert color="blue" mt="md">Loading backtest…</Alert>}
      {error && <Alert color="red" mt="md">Failed: {String(error)}</Alert>}

      {data && (
        <>
          <Group mt="md">
            <Badge>CAGR {data.kpis.cagr_pct.toFixed(2)}%</Badge>
            <Badge>Sharpe {data.kpis.sharpe.toFixed(2)}</Badge>
            <Badge>Sortino {data.kpis.sortino.toFixed(2)}</Badge>
            <Badge>MaxDD {data.kpis.max_drawdown_pct.toFixed(1)}%</Badge>
            <Badge>WinRate {data.kpis.win_rate_pct.toFixed(1)}%</Badge>
          </Group>

          <SimpleGrid cols={{ base: 1, md: 2 }} mt="lg">
            <AreaChart
              data={data.equity_curve}
              index="date"
              categories={['strategy', ...(data.equity_curve.some((row) => row.benchmark != null) ? ['benchmark'] : [])]}
              yAxisWidth={56}
            />
            <BarChart
              data={(data.monthly_returns ?? []).map((row) => ({ month: row.month, returns: row.pct }))}
              index="month"
              categories={['returns']}
              yAxisWidth={56}
            />
          </SimpleGrid>
        </>
      )}
    </Card>
  );
}
