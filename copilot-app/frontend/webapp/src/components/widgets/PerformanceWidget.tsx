/**
 * PerformanceWidget
 *
 * Displays portfolio/backtest performance using real backend APIs:
 * - /api/backtests (overall metrics)
 * - /api/backtests/efficient_frontier (optional frontier summary)
 */
import { Card, Stack, Group, Title, Text, Badge, Skeleton, ActionIcon, SimpleGrid } from '@mantine/core';
import { IconGauge, IconRefresh } from '@tabler/icons-react';
import { BarList } from '@tremor/react';
import { useEfficientFrontier } from '@/hooks/useEfficientFrontier';
import { api } from '@/api/client';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import { useEffect, useState } from 'react';

type BacktestsResponse = {
  overall_metrics?: {
    hit_rate?: number;
    avg_return?: number;
    sharpe_ratio?: number;
    max_drawdown?: number;
    n_trades?: number;
  };
  freshness?: string;
  generated_at?: string;
};

export function PerformanceWidget() {
  const [data, setData] = useState<BacktestsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { data: frontier, isLoading: frontierLoading } = useEfficientFrontier();

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const json = await api.fetchJson<any>('/api/backtests');
      const payload = (json?.data ?? json) as BacktestsResponse;
      setData(payload);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const header = (
    <Group justify="space-between" align="center">
      <Group gap="xs" align="center">
        <div className={sharedStyles.sparkIcon}>
          <IconGauge size={18} />
        </div>
        <Title order={4}>Performance</Title>
      </Group>
      <ActionIcon size="sm" variant="light" color="blue" onClick={load} loading={loading} aria-label="Rafraîchir">
        <IconRefresh size={16} />
      </ActionIcon>
    </Group>
  );

  if (loading) {
    return (
      <Card padding="lg" radius="xl" className={sharedStyles.glassCard}>
        <Stack gap="md">
          {header}
          <Skeleton height={16} width="60%" radius="xl" />
          <SimpleGrid cols={{ base: 2, md: 4 }}>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} height={64} radius="md" />
            ))}
          </SimpleGrid>
          <Skeleton height={140} radius="md" />
        </Stack>
      </Card>
    );
  }

  if (error) {
    return (
      <Card padding="lg" radius="xl" className={sharedStyles.glassCard}>
        <Stack gap="md">
          {header}
          <Text size="sm" c="red.6">Erreur: {error}</Text>
        </Stack>
      </Card>
    );
  }

  const m = data?.overall_metrics || {};
  const pct = (x?: number | null) => (typeof x === 'number' ? `${(x * 100).toFixed(2)}%` : '—');
  const pctRaw = (x?: number | null) => (typeof x === 'number' ? `${x.toFixed(2)}%` : '—');

  // Build a compact frontier summary for BarList (top 5 Sharpe)
  const frontierList = (frontier?.frontier || [])
    .slice()
    .sort((a, b) => (b.sharpe ?? 0) - (a.sharpe ?? 0))
    .slice(0, 5)
    .map((p) => ({ name: `Sharpe ${p.sharpe?.toFixed(2)} · σ ${p.risk?.toFixed(2)}%`, value: Number((p.return ?? 0).toFixed(2)) }));

  return (
    <Card padding="lg" radius="xl" className={sharedStyles.glassCard}>
      <Stack gap="md">
        {header}
        <SimpleGrid cols={{ base: 2, md: 4 }}>
          <Card withBorder padding="sm" radius="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed">Hit Rate</Text>
              <Text fw={700}>{pct(m.hit_rate)}</Text>
            </Stack>
          </Card>
          <Card withBorder padding="sm" radius="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed">Avg Return</Text>
              <Text fw={700}>{pct(m.avg_return)}</Text>
            </Stack>
          </Card>
          <Card withBorder padding="sm" radius="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed">Sharpe</Text>
              <Text fw={700}>{typeof m.sharpe_ratio === 'number' ? m.sharpe_ratio.toFixed(2) : '—'}</Text>
            </Stack>
          </Card>
          <Card withBorder padding="sm" radius="md">
            <Stack gap={2}>
              <Text size="xs" c="dimmed">Max Drawdown</Text>
              <Text fw={700}>{pctRaw(m.max_drawdown)}</Text>
            </Stack>
          </Card>
        </SimpleGrid>
        <div>
          <Group justify="space-between" align="center">
            <Text size="sm" fw={600}>Efficient Frontier (top Sharpe)</Text>
            {frontierLoading && <Badge variant="light">Loading…</Badge>}
          </Group>
          <div style={{ marginTop: 6 }}>
            {frontierList.length > 0 ? (
              <BarList data={frontierList} valueFormatter={(n) => `${n.toFixed(2)}%`} />
            ) : (
              <Text size="sm" c="dimmed">Données d'Efficient Frontier indisponibles</Text>
            )}
          </div>
        </div>
        <Text size="xs" c="dimmed">MAJ {new Date(data?.freshness || data?.generated_at || new Date().toISOString()).toLocaleString()}</Text>
      </Stack>
    </Card>
  );
}

export default PerformanceWidget;

