import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/api/client';
import { Button, Card, Chip, Heading, LoadingSpinner, RingProgress, SimpleGrid, Stack, Text, Group } from '@/ui';
import FreshnessBadge from '@/components/ui/FreshnessBadge';
import EmptyState from '@/components/ui/EmptyState';

interface BacktestResult {
  results?: {
    ok?: boolean;
    count_days?: number;
    avg_basket_return?: number;
    median?: number;
    stdev?: number;
    error?: string;
  };
  params?: {
    horizon?: string;
    top_n?: number;
    days_back?: number;
  };
  generated_at?: string;
  warning?: string;
  detailed_results?: Array<Record<string, any>>;
  cache_status?: string;
}

const HORIZONS: Array<{ label: string; value: '1w' | '1m' | '1y' }> = [
  { label: '1 semaine', value: '1w' },
  { label: '1 mois', value: '1m' },
  { label: '1 an', value: '1y' },
];

const TOP_OPTIONS = [3, 5, 10];

export default function Backtests() {
  const [horizon, setHorizon] = useState<'1w' | '1m' | '1y'>('1m');
  const [topN, setTopN] = useState<number>(5);
  const [daysBack, setDaysBack] = useState<number>(180);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['backtests', horizon, topN, daysBack],
    queryFn: async () => {
      const response = await apiGet<BacktestResult>('/backtests', {
        horizon,
        top_n: String(topN),
        days_back: String(daysBack),
      });
      if (!response.ok) throw new Error(response.error || 'Backtests indisponibles');
      return response.data;
    },
    staleTime: 300_000,
  });

  const summary = data?.results;
  const freshness = data?.generated_at ?? null;
  const hasData = summary && summary.ok && summary.count_days && summary.count_days > 0;

  return (
    <Stack gap="xl">
      <Group justify="space-between" align="center">
        <Stack gap={0}>
          <Heading order={2}>Backtests — Performance historique</Heading>
          <Text c="dimmed">Évalue la stratégie en rejouant les signaux passés.</Text>
        </Stack>
        {freshness && <FreshnessBadge freshness={freshness} />}
      </Group>

      <Card>
        <Stack gap="md">
          <Heading order={4}>Paramètres</Heading>
          <Group>
            {HORIZONS.map((option) => (
              <Chip
                key={option.value}
                checked={horizon === option.value}
                onChange={() => setHorizon(option.value)}
              >
                {option.label}
              </Chip>
            ))}
          </Group>
          <Group>
            {TOP_OPTIONS.map((value) => (
              <Chip
                key={value}
                checked={topN === value}
                onChange={() => setTopN(value)}
              >
                Top {value}
              </Chip>
            ))}
          </Group>
          <Group>
            {[90, 180, 365].map((value) => (
              <Chip
                key={value}
                checked={daysBack === value}
                onChange={() => setDaysBack(value)}
              >
                {value}j historique
              </Chip>
            ))}
          </Group>
          <Button variant="light" onClick={() => refetch()} disabled={isLoading}>
            Rafraîchir les backtests
          </Button>
        </Stack>
      </Card>

      {isLoading && (
        <Stack align="center" gap="xs">
          <LoadingSpinner />
          <Text c="dimmed">Chargement des résultats…</Text>
        </Stack>
      )}

      {error && (
        <Card>
          <Text c="red">Erreur: {String(error)}</Text>
        </Card>
      )}

      {!isLoading && !hasData && !error && (
        <EmptyState
          title="Aucun backtest disponible"
          subtitle={data?.warning || 'Le calcul est en arrière-plan. Revenez plus tard.'}
        />
      )}

      {hasData && summary && (
        <SimpleGrid cols={{ base: 1, md: 3 }} spacing="lg">
          <Card>
            <Stack align="center" gap="xs">
              <Text c="dimmed" fz="sm">Retour moyen panier</Text>
              <RingProgress
                size={120}
                thickness={14}
                sections={[{ value: Math.min(100, Math.max(0, (summary.avg_basket_return ?? 0) * 2000)), color: summary.avg_basket_return && summary.avg_basket_return > 0 ? 'teal' : 'red' }]}
                label={<Text fw={700}>{((summary.avg_basket_return ?? 0) * 100).toFixed(2)}%</Text>}
              />
            </Stack>
          </Card>
          <Card>
            <Stack align="center" gap="xs">
              <Text c="dimmed" fz="sm">Médiane</Text>
              <Text fw={700} fz="xl">{((summary.median ?? 0) * 100).toFixed(2)}%</Text>
              <Text c="dimmed" fz="xs">Nombre de jours: {summary.count_days}</Text>
            </Stack>
          </Card>
          <Card>
            <Stack align="center" gap="xs">
              <Text c="dimmed" fz="sm">Volatilité (Stdev)</Text>
              <Text fw={700} fz="xl">{((summary.stdev ?? 0) * 100).toFixed(2)}%</Text>
              <Text c="dimmed" fz="xs">Statut cache: {data?.cache_status ?? 'n/a'}</Text>
            </Stack>
          </Card>
        </SimpleGrid>
      )}

      {data?.warning && (
        <Card>
          <Text c="orange">⚠️ {data.warning}</Text>
        </Card>
      )}

      {data?.detailed_results && data.detailed_results.length > 0 && (
        <Card>
          <Stack gap="md">
            <Heading order={4}>Résultats détaillés</Heading>
            <SimpleGrid cols={{ base: 1, md: 2, lg: 3 }} spacing="md">
              {data.detailed_results.map((row, idx) => (
                <Card key={idx} radius="md" shadow="sm">
                  <Stack gap={4}>
                    <Text fw={600}>{row.period ?? `Itération ${idx + 1}`}</Text>
                    <Text c="dimmed" fz="xs">Retour {(Number(row.return ?? 0) * 100).toFixed(2)}%</Text>
                    {'sharpe' in row && <Text fz="xs">Sharpe {(Number(row.sharpe ?? 0)).toFixed(2)}</Text>}
                    {'max_dd' in row && <Text fz="xs">Max DD {(Number(row.max_dd ?? 0)).toFixed(2)}</Text>}
                  </Stack>
                </Card>
              ))}
            </SimpleGrid>
          </Stack>
        </Card>
      )}
    </Stack>
  );
}
