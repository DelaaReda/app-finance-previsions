/**
 * Health & Freshness Overview Page
 *
 * Displays system health, data freshness, and monitoring metrics.
 *
 * Features:
 * - Real-time health status for all datasets
 * - Latency tracking and thresholds
 * - Color-coded freshness badges
 * - Debug JSON accordion for troubleshooting
 * - Auto-refresh every 60s
 *
 * Author: CLAUDE-CODE
 * Task: FC-PHASE1-002 - Health & Freshness Overview
 */

import { Container, Title, Text, Grid, Card, Badge, Group, Stack, Alert, Progress, Accordion, Code, ActionIcon } from '@mantine/core';
import { IconActivity, IconAlertCircle, IconCheck, IconClock, IconRefresh, IconChevronDown } from '@tabler/icons-react';
import { useHealth } from '@/hooks/useHealth';
import { useForecasts } from '@/hooks/useForecasts';
import { useNewsCompat } from '@/hooks/useNewsCompat';

/**
 * Format latency in human-readable form
 */
function formatLatency(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}j`;
}

/**
 * Get color based on freshness threshold
 */
function getFreshnessColor(latencySec: number, datasetName: string): string {
  // Thresholds: forecasts 1h, news 10min, macro 3 days
  const thresholds: Record<string, number> = {
    forecasts: 3600,      // 1h
    news_feed: 600,       // 10min
    news: 600,            // 10min
    macro: 259200,        // 3 days
    backtests: 86400,     // 1 day
    brief_weekly: 604800, // 7 days
  };

  const threshold = thresholds[datasetName] || 3600; // Default 1h

  if (latencySec <= threshold) return 'green';
  if (latencySec <= threshold * 2) return 'yellow';
  return 'red';
}

/**
 * Get status icon based on freshness
 */
function getStatusIcon(latencySec: number, datasetName: string) {
  const color = getFreshnessColor(latencySec, datasetName);

  if (color === 'green') return <IconCheck size={20} color="green" />;
  if (color === 'yellow') return <IconClock size={20} color="orange" />;
  return <IconAlertCircle size={20} color="red" />;
}

/**
 * Dataset Health Card Component
 */
function DatasetHealthCard({
  name,
  last_update,
  latency_sec,
  errors_24h
}: {
  name: string;
  last_update: string;
  latency_sec: number;
  errors_24h: number;
}) {
  const color = getFreshnessColor(latency_sec, name);
  const progressValue = Math.min(100, (latency_sec / 3600) * 100); // % of 1h

  return (
    <Card withBorder shadow="sm" padding="lg" radius="md" data-testid="dataset-health-card">
      <Stack gap="md">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Group gap="xs" align="center">
              {getStatusIcon(latency_sec, name)}
              <Text fw={600} size="lg">
                {name}
              </Text>
            </Group>
            <Text size="xs" c="dimmed" mt={4}>
              Dernière mise à jour: {new Date(last_update).toLocaleString('fr-FR')}
            </Text>
          </div>
          <Badge color={color} variant="light" size="lg">
            {formatLatency(latency_sec)}
          </Badge>
        </Group>

        {/* Latency Progress */}
        <div>
          <Group justify="space-between" mb={4}>
            <Text size="xs" c="dimmed">Latence</Text>
            <Text size="xs" c="dimmed">{latency_sec}s</Text>
          </Group>
          <Progress value={progressValue} color={color} size="sm" radius="xl" />
        </div>

        {/* Errors */}
        {errors_24h > 0 && (
          <Alert color="red" variant="light" icon={<IconAlertCircle size={16} />}>
            <Text size="xs">
              {errors_24h} erreur{errors_24h > 1 ? 's' : ''} dans les dernières 24h
            </Text>
          </Alert>
        )}
      </Stack>
    </Card>
  );
}

/**
 * Main Health Page Component
 */
export default function HealthPage() {
  const { data: health, isLoading, error, refetch, isFetching } = useHealth();
  const forecastsQ = useForecasts({ horizon: 'short' });
  const newsQ = useNewsCompat();

  // Overall system status
  const allHealthy = health?.datasets.every(d => getFreshnessColor(d.latency_sec, d.name) === 'green') ?? false;
  const systemStatus = allHealthy ? 'up' : error ? 'down' : 'degraded';
  const statusColor = systemStatus === 'up' ? 'green' : systemStatus === 'degraded' ? 'yellow' : 'red';

  return (
    <Container size="xl" py="xl">
      <Stack gap="xl">
        {/* Header */}
        <div>
          <Group justify="space-between" align="flex-start">
            <div>
              <Title order={1} fw={700} size="h1">
                Health & Freshness Overview
              </Title>
              <Text c="dimmed" size="sm" mt={4}>
                Surveillance en temps réel de l'état du système et de la fraîcheur des données
              </Text>
            </div>
            <ActionIcon
              variant="light"
              size="lg"
              onClick={() => refetch()}
              loading={isFetching}
              aria-label="Rafraîchir"
            >
              <IconRefresh size={20} />
            </ActionIcon>
          </Group>
        </div>

        {/* System Status Banner */}
        <Alert
          color={statusColor}
          variant="light"
          icon={systemStatus === 'up' ? <IconCheck size={20} /> : <IconAlertCircle size={20} />}
          styles={{
            root: { borderLeft: `4px solid var(--mantine-color-${statusColor}-6)` }
          }}
          data-testid="health-status-banner"
        >
          <Group justify="space-between">
            <div>
              <Text fw={600} size="lg">
                Système: {systemStatus === 'up' ? 'Opérationnel' : systemStatus === 'degraded' ? 'Dégradé' : 'Hors ligne'}
              </Text>
              <Text size="sm" c="dimmed" mt={4}>
                {health?.datasets.length ?? 0} dataset{(health?.datasets.length ?? 0) > 1 ? 's' : ''} surveillé{(health?.datasets.length ?? 0) > 1 ? 's' : ''}
                {health?.updated_at && ` • Dernière vérification: ${new Date(health.updated_at).toLocaleString('fr-FR')}`}
              </Text>
            </div>
            <Badge color={statusColor} size="xl" variant="filled">
              {systemStatus.toUpperCase()}
            </Badge>
          </Group>
        </Alert>

        {/* Error State */}
        {error && (
          <Alert color="red" icon={<IconAlertCircle size={20} />} title="Erreur de chargement">
            <Text size="sm">
              Impossible de récupérer l'état de santé du système. Veuillez réessayer.
            </Text>
          </Alert>
        )}

        {/* Loading State */}
        {isLoading && !health && (
          <Card withBorder padding="xl">
            <Stack align="center" gap="md">
              <IconActivity size={40} color="blue" />
              <Text>Chargement de l'état de santé...</Text>
            </Stack>
          </Card>
        )}

        {/* Datasets Health Grid */}
        {health && (
          <Grid gutter="lg">
            {health.datasets.map((dataset) => (
              <Grid.Col key={dataset.name} span={{ base: 12, md: 6, lg: 4 }}>
                <DatasetHealthCard {...dataset} />
              </Grid.Col>
            ))}
          </Grid>
        )}

        {/* Summary Stats */}
        {health && (
          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Card withBorder shadow="sm" padding="lg">
                <Stack gap="xs">
                  <Text size="sm" c="dimmed" fw={500}>
                    Datasets Sains
                  </Text>
                  <Group align="baseline" gap="xs">
                    <Text fw={700} size="2rem">
                      {health.datasets.filter(d => getFreshnessColor(d.latency_sec, d.name) === 'green').length}
                    </Text>
                    <Text size="sm" c="dimmed">
                      / {health.datasets.length}
                    </Text>
                  </Group>
                </Stack>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 4 }}>
              <Card withBorder shadow="sm" padding="lg">
                <Stack gap="xs">
                  <Text size="sm" c="dimmed" fw={500}>
                    Prévisions Disponibles
                  </Text>
                  <Text fw={700} size="2rem">
                    {forecastsQ.data?.items?.length ?? 0}
                  </Text>
                </Stack>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 4 }}>
              <Card withBorder shadow="sm" padding="lg">
                <Stack gap="xs">
                  <Text size="sm" c="dimmed" fw={500}>
                    Articles News
                  </Text>
                  <Text fw={700} size="2rem">
                    {newsQ.articles?.length ?? 0}
                  </Text>
                </Stack>
              </Card>
            </Grid.Col>
          </Grid>
        )}

        {/* Debug JSON Accordion */}
        {health && (
          <Accordion variant="separated">
            <Accordion.Item value="debug-json">
              <Accordion.Control icon={<IconChevronDown size={20} />}>
                <Group gap="xs">
                  <Text fw={600}>Données brutes (Debug)</Text>
                  <Badge size="xs" variant="light">JSON</Badge>
                </Group>
              </Accordion.Control>
              <Accordion.Panel>
                <Code block style={{ maxHeight: 400, overflow: 'auto' }}>
                  {JSON.stringify(health, null, 2)}
                </Code>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        )}

        {/* Thresholds Reference */}
        <Card withBorder padding="lg">
          <Stack gap="md">
            <Text fw={600} size="lg">
              Seuils de Fraîcheur
            </Text>
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Stack gap={4}>
                  <Badge color="green" variant="light">Forecasts</Badge>
                  <Text size="xs" c="dimmed">Seuil: 1 heure</Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Stack gap={4}>
                  <Badge color="blue" variant="light">News</Badge>
                  <Text size="xs" c="dimmed">Seuil: 10 minutes</Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Stack gap={4}>
                  <Badge color="violet" variant="light">Macro</Badge>
                  <Text size="xs" c="dimmed">Seuil: 3 jours</Text>
                </Stack>
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                <Stack gap={4}>
                  <Badge color="orange" variant="light">Backtests</Badge>
                  <Text size="xs" c="dimmed">Seuil: 1 jour</Text>
                </Stack>
              </Grid.Col>
            </Grid>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
