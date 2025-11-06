/**
 * Forecast Detail Drawer
 *
 * Slide-over panel showing comprehensive forecast details.
 *
 * Features:
 * - Model version and components
 * - Sparkline trend visualization
 * - Top features contributing to forecast
 * - Related news articles for the ticker
 * - Pin to dashboard action
 * - Navigation to ticker details
 *
 * Author: CLAUDE-CODE
 * Task: FC-PHASE1-003 - Forecast Detail Drawer
 */

import { Drawer, Stack, Group, Text, Badge, Button, ActionIcon, Divider, Card, Timeline, Alert, Loader } from '@mantine/core';
import { Line Chart as MiniLineChart } from '@/components/charts/MiniLineChart';
import { IconX, IconPinFilled, IconPin, IconExternalLink, IconTrendingUp, IconTrendingDown, IconClock, IconInfoCircle } from '@tabler/icons-react';
import { useNewsCompat } from '@/hooks/useNewsCompat';
import type { ForecastItem } from '@/types/forecast';
import { useState } from 'react';

interface ForecastDetailDrawerProps {
  opened: boolean;
  onClose: () => void;
  forecast: ForecastItem | null;
  onPinToDashboard?: (ticker: string) => void;
  onNavigateToTicker?: (ticker: string) => void;
}

/**
 * Format confidence as percentage
 */
function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/**
 * Format expected return
 */
function formatExpectedReturn(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Get direction badge props
 */
function getDirectionBadge(direction: string): { label: string; color: string } {
  if (direction === 'up') return { label: 'Haussier', color: 'green' };
  if (direction === 'down') return { label: 'Baissier', color: 'red' };
  return { label: 'Neutre', color: 'gray' };
}

/**
 * Forecast Detail Drawer Component
 */
export function ForecastDetailDrawer({
  opened,
  onClose,
  forecast,
  onPinToDashboard,
  onNavigateToTicker,
}: ForecastDetailDrawerProps) {
  const [isPinned, setIsPinned] = useState(false);

  const ticker = forecast?.ticker ?? forecast?.symbol ?? '';
  const newsQ = useNewsCompat({ tickers: ticker ? [ticker] : [] });

  const handlePin = () => {
    if (ticker && onPinToDashboard) {
      onPinToDashboard(ticker);
      setIsPinned(!isPinned);
    }
  };

  const handleNavigate = () => {
    if (ticker && onNavigateToTicker) {
      onNavigateToTicker(ticker);
      onClose();
    }
  };

  if (!forecast) {
    return (
      <Drawer opened={opened} onClose={onClose} position="right" size="lg" title="Détails de la Prévision">
        <Alert color="yellow" icon={<IconInfoCircle size={20} />}>
          Aucune prévision sélectionnée
        </Alert>
      </Drawer>
    );
  }

  const directionBadge = getDirectionBadge(forecast.direction);
  const confidence = forecast.confidence ?? 0;
  const expectedReturn = (forecast.expected_return_pct ?? forecast.expectedReturnPct ?? 0) / 100;

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="right"
      size="lg"
      title={
        <Group gap="md" align="center">
          <Text fw={700} size="xl">{ticker}</Text>
          <Badge color={directionBadge.color} size="lg" variant="light">
            {directionBadge.label}
          </Badge>
        </Group>
      }
      styles={{
        header: {
          paddingBottom: '1rem',
          borderBottom: '1px solid #e9ecef'
        }
      }}
    >
      <Stack gap="lg">
        {/* Actions */}
        <Group gap="xs">
          <Button
            leftSection={isPinned ? <IconPinFilled size={16} /> : <IconPin size={16} />}
            variant={isPinned ? 'filled' : 'light'}
            size="sm"
            onClick={handlePin}
          >
            {isPinned ? 'Épinglé' : 'Épingler au dashboard'}
          </Button>
          <Button
            leftSection={<IconExternalLink size={16} />}
            variant="light"
            size="sm"
            onClick={handleNavigate}
          >
            Voir la page ticker
          </Button>
        </Group>

        {/* Key Metrics */}
        <Card withBorder padding="md">
          <Stack gap="md">
            <Text fw={600} size="lg">Métriques Clés</Text>

            <Group grow>
              <div>
                <Text size="xs" c="dimmed" mb={4}>Score</Text>
                <Text fw={700} size="xl" c={forecast.score >= 70 ? 'green' : forecast.score >= 40 ? 'yellow' : 'red'}>
                  {forecast.score}/100
                </Text>
              </div>
              <div>
                <Text size="xs" c="dimmed" mb={4}>Confiance</Text>
                <Text fw={700} size="xl">{formatConfidence(confidence)}</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed" mb={4}>Rendement Attendu</Text>
                <Group gap={4} align="baseline">
                  {expectedReturn > 0 ? <IconTrendingUp size={16} color="green" /> : <IconTrendingDown size={16} color="red" />}
                  <Text fw={700} size="xl" c={expectedReturn > 0 ? 'green' : 'red'}>
                    {formatExpectedReturn(expectedReturn)}
                  </Text>
                </Group>
              </div>
            </Group>

            <Divider />

            <Group justify="space-between">
              <Text size="sm" c="dimmed">Horizon</Text>
              <Badge variant="light">{forecast.horizon}</Badge>
            </Group>

            {(forecast.forecasted_at || forecast.updatedAt) && (
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Dernière MAJ</Text>
                <Group gap={4}>
                  <IconClock size={14} />
                  <Text size="sm">{new Date(forecast.forecasted_at ?? forecast.updatedAt!).toLocaleString('fr-FR')}</Text>
                </Group>
              </Group>
            )}
          </Stack>
        </Card>

        {/* Model Information */}
        {forecast.model_version && (
          <Card withBorder padding="md">
            <Stack gap="sm">
              <Text fw={600} size="lg">Modèle</Text>
              <Group justify="space-between">
                <Text size="sm" c="dimmed">Version</Text>
                <Badge variant="dot">{forecast.model_version}</Badge>
              </Group>
            </Stack>
          </Card>
        )}

        {/* Top Features */}
        {forecast.top_features && forecast.top_features.length > 0 && (
          <Card withBorder padding="md">
            <Stack gap="md">
              <Text fw={600} size="lg">Facteurs Principaux</Text>
              <Timeline active={-1} bulletSize={24} lineWidth={2}>
                {forecast.top_features.slice(0, 5).map((feature, idx) => (
                  <Timeline.Item
                    key={idx}
                    title={<Text size="sm" fw={500}>{feature.name ?? `Feature ${idx + 1}`}</Text>}
                  >
                    <Group gap="xs" mt={4}>
                      <Badge size="sm" variant="light" color={feature.importance > 0.5 ? 'blue' : 'gray'}>
                        {Math.round((feature.importance ?? 0) * 100)}% importance
                      </Badge>
                      {feature.value !== undefined && (
                        <Text size="xs" c="dimmed">Valeur: {feature.value.toFixed(4)}</Text>
                      )}
                    </Group>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Stack>
          </Card>
        )}

        {/* Related News */}
        <Card withBorder padding="md">
          <Stack gap="md">
            <Group justify="space-between">
              <Text fw={600} size="lg">Actualités Liées</Text>
              <Badge variant="light">{newsQ.articles?.length ?? 0} articles</Badge>
            </Group>

            {newsQ.loading && (
              <Group justify="center" py="md">
                <Loader size="sm" />
                <Text size="sm" c="dimmed">Chargement des actualités...</Text>
              </Group>
            )}

            {newsQ.error && (
              <Alert color="red" variant="light" icon={<IconInfoCircle size={16} />}>
                <Text size="sm">Impossible de charger les actualités</Text>
              </Alert>
            )}

            {!newsQ.loading && !newsQ.error && newsQ.articles && newsQ.articles.length > 0 && (
              <Stack gap="sm">
                {newsQ.articles.slice(0, 5).map((article, idx) => (
                  <Card key={idx} withBorder padding="sm" style={{ backgroundColor: '#f8f9fa' }}>
                    <Stack gap={4}>
                      <Text size="sm" fw={500} lineClamp={2}>
                        {article.title}
                      </Text>
                      <Group gap="xs">
                        {article.source && (
                          <Badge size="xs" variant="dot">{article.source}</Badge>
                        )}
                        {article.published_at && (
                          <Text size="xs" c="dimmed">
                            {new Date(article.published_at).toLocaleDateString('fr-FR')}
                          </Text>
                        )}
                      </Group>
                    </Stack>
                  </Card>
                ))}
              </Stack>
            )}

            {!newsQ.loading && !newsQ.error && (!newsQ.articles || newsQ.articles.length === 0) && (
              <Text size="sm" c="dimmed" ta="center" py="md">
                Aucune actualité récente pour {ticker}
              </Text>
            )}
          </Stack>
        </Card>

        {/* Reason/Explanation */}
        {forecast.reason && (
          <Card withBorder padding="md" style={{ backgroundColor: '#f0f7ff' }}>
            <Stack gap="xs">
              <Text fw={600} size="sm">Explication</Text>
              <Text size="sm" c="dimmed">{forecast.reason}</Text>
            </Stack>
          </Card>
        )}
      </Stack>
    </Drawer>
  );
}
