/**
 * RisksWidget
 *
 * Adaptive widget backed by /api/brief/weekly.
 * Displays top bearish signals (risks) to watch.
 */
import { Card, Stack, Group, Title, Text, Badge, ActionIcon, Skeleton, Button, ScrollArea } from '@mantine/core';
import { IconTrendingDown, IconArrowRight, IconRefresh } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '@/hooks/useApi';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';

type BriefRisk = {
  ticker: string;
  type?: string; // BEARISH | BULLISH
  confidence?: number; // 0..1
  expected_return?: number; // fraction e.g. 0.012
  horizon?: string;
  reasoning?: string;
};

export function RisksWidget() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useApi<any>('/api/brief/weekly');

  // Normalize payload: prefer data.top_risks; otherwise try nested structures
  const brief = (data?.data ?? data) || {};
  const rawRisks: BriefRisk[] = Array.isArray(brief?.top_risks)
    ? brief.top_risks
    : Array.isArray(brief?.risks)
      ? brief.risks
      : [];

  // Keep only bearish signals as risks
  const risks = rawRisks
    .filter((s) => (s?.type || 'BEARISH').toUpperCase() === 'BEARISH')
    .slice(0, 6);

  const header = (
    <Group justify="space-between" align="center">
      <Group gap="xs" align="center">
        <div className={sharedStyles.sparkIcon}>
          <IconTrendingDown size={18} />
        </div>
        <Title order={4}>Risques hebdo</Title>
      </Group>
      <Group gap="xs">
        <Button size="xs" variant="light" onClick={() => navigate('/brief')}>
          Voir plus
        </Button>
        <ActionIcon size="sm" variant="light" color="red" onClick={() => refetch()} loading={isLoading} aria-label="Rafraîchir">
          <IconRefresh size={16} />
        </ActionIcon>
      </Group>
    </Group>
  );

  if (isLoading) {
    return (
      <Card padding="lg" radius="xl" className={sharedStyles.glassCard}>
        <Stack gap="md">
          {header}
          {Array.from({ length: 3 }).map((_, i) => (
            <Group key={i} justify="space-between">
              <Skeleton height={14} width="80px" radius="xl" />
              <Skeleton height={14} width="60px" radius="xl" />
              <Skeleton height={14} width="80px" radius="xl" />
            </Group>
          ))}
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
          <Button size="xs" variant="light" onClick={() => refetch()}>Réessayer</Button>
        </Stack>
      </Card>
    );
  }

  return (
    <Card padding="md" radius="lg" className={sharedStyles.glassCard}>
      <Stack gap="md">
        {header}
        <ScrollArea style={{ maxHeight: 300 }} type="auto">
          <Stack gap="sm">
            {risks.map((s, idx) => {
              const conf = s.confidence != null ? Math.round(s.confidence * 100) : undefined;
              const er = s.expected_return != null ? (s.expected_return * 100) : undefined;
              return (
                <Group key={`${s.ticker}-${idx}`} justify="space-between" wrap="wrap">
                  <Group gap={8} align="center">
                    <Badge color="red" variant="light">{s.ticker}</Badge>
                    <Text size="sm" c="dimmed">{s.horizon ?? '1d'}</Text>
                  </Group>
                  <Group gap="xs">
                    {conf != null && (
                      <Badge variant="light" color={conf >= 70 ? 'red' : conf >= 40 ? 'yellow' : 'gray'}>
                        Confiance {conf}%
                      </Badge>
                    )}
                    {er != null && (
                      <Badge variant="light" color={er >= 0 ? 'red' : 'green'}>
                        ER {er.toFixed(2)}%
                      </Badge>
                    )}
                    <ActionIcon size="sm" variant="subtle" aria-label="Voir" onClick={() => navigate(`/stocks/${s.ticker}`)}>
                      <IconArrowRight size={16} />
                    </ActionIcon>
                  </Group>
                </Group>
              );
            })}
          </Stack>
        </ScrollArea>
        {risks.length === 0 && (
          <Text size="sm" c="dimmed">Aucun risque saillant détecté pour le moment.</Text>
        )}
      </Stack>
    </Card>
  );
}

export default RisksWidget;
