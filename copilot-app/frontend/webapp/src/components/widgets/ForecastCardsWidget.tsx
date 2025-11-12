/**
 * ForecastCardsWidget Component
 * Displays forecast cards with scores and confidence measures
 */

import { useState, useMemo } from 'react';
import {
  Group,
  Alert,
  SegmentedControl,
  Tooltip,
  Button,
  Card as MantineCard,
  Title,
  Text,
  RingProgress,
  Badge as MantineBadge,
  ScrollArea,
  Stack,
  Skeleton
} from '@mantine/core';
import { IconAlertCircle, IconInfoCircle } from '@tabler/icons-react';
import { BadgeDelta } from '@tremor/react';
import { formatFractionToPercent, formatPercentage } from '@/lib/utils';
import { formatPercent, formatConfidence, getConfidenceColor } from '@/lib/formatting';
import { useForecasts } from '@/hooks/useForecasts';
import type { ForecastHorizon } from '@/types/forecast';
import { ensureArray, safeGet } from '@/lib/safe';
import { ForecastDetailDrawer } from '@/components/forecasts/ForecastDetailDrawer';
import { useNavigate } from 'react-router-dom';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import styles from './ForecastCardsWidget.module.css';

type Props = {
  universe: string[];
  initialHorizon?: ForecastHorizon;
  limit?: number;
  title?: string;
  onSelectTicker?: (ticker: string) => void;
  onOpenDetails?: (ticker: string) => void;
};

function dirToDelta(d: 'up' | 'down' | 'neutral' | 'flat') {
  if (d === 'up') return 'increase';
  if (d === 'down') return 'decrease';
  return 'unchanged';
}

function dirToBadge(d: 'up' | 'down' | 'neutral' | 'flat') {
  if (d === 'up') return { label: 'Haussier', color: 'green' as const };
  if (d === 'down') return { label: 'Baissier', color: 'red' as const };
  return { label: 'Neutre', color: 'gray' as const };
}

function fmtPct(x: number) {
  const sign = x > 0 ? '+' : x < 0 ? '−' : '';
  return `${sign}${Math.abs(x).toFixed(2)}%`;
}

export function ForecastCardsWidget({
  universe,
  initialHorizon = 'short',
  limit = 12,
  title = 'Prévisions (cartes)',
  onSelectTicker,
  onOpenDetails,
}: Props) {
  const [hz, setHz] = useState<ForecastHorizon>(initialHorizon);
  const [drawerOpened, setDrawerOpened] = useState(false);
  const [selectedForecast, setSelectedForecast] = useState<any>(null);
  const navigate = useNavigate();
  const forecastFilters = {
    horizon: hz,
    tickers: universe && universe.length > 0 ? universe : undefined,
    limit,
  };
  const { data, isLoading, error, refetch, isFetching } = useForecasts(forecastFilters);
  
  const handleOpenDetails = (forecast: any) => {
    setSelectedForecast(forecast);
    setDrawerOpened(true);
  };
  
  const handleCloseDrawer = () => {
    setDrawerOpened(false);
    setSelectedForecast(null);
  };
  
  const handleNavigateToTicker = (ticker: string) => {
    if (onSelectTicker) {
      onSelectTicker(ticker);
    } else {
      navigate(`/stocks/${ticker}`);
    }
    handleCloseDrawer();
  };

  const items = useMemo(() => {
    const arr = ensureArray(safeGet(data, 'rows', [])).slice();
    // Use confidence as score if score is not available
    arr.forEach(item => {
      if (item.score === undefined && item.confidence !== undefined) {
        item.score = Math.round(item.confidence * 100);
      }
      if (item.expected_return_pct === undefined && item.expected_return !== undefined) {
        item.expected_return_pct = item.expected_return * 100;
      }
    });
    arr.sort((a, b) => (b.score ?? 0) - (a.score ?? 0) || ((b.confidence ?? 0) - (a.confidence ?? 0)));
    return arr.slice(0, limit);
  }, [data, limit]);

  const exportCsv = () => {
    const lines: string[] = [];
    lines.push('symbol,horizon,score,confidence,direction,expected_return_pct,updated_at');

    ensureArray(safeGet(data, 'rows', [])).forEach((f) => {
      lines.push([
        f.ticker ?? f.symbol ?? '',
        f.horizon,
        f.score,
        Math.round((f.confidence ?? 0) * 100) / 100,
        f.direction,
        ((f.expected_return_pct ?? f.expectedReturnPct ?? 0)).toFixed(4),
        f.forecasted_at ?? f.updatedAt ?? '',
      ].join(','));
    });
    
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `forecasts-${hz}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const hasItems = ensureArray(items).length > 0;
  const showSkeletons = isLoading && !error;

  return (
    <MantineCard
      padding="lg"
      radius="xl"
      className={`${sharedStyles.glassCard} ${styles.widgetCard}`}
    >
      <Stack gap="md" style={{ flex: 1, minHeight: 0 }} className={styles.contentStack}>
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            <Title order={4}>{title}</Title>
            <Text c="dimmed" size="sm">
              Classement par score et confiance • Horizon{' '}
              <Text span fw={600}>
                {hz}
              </Text>
            </Text>
          </div>
          <div className={styles.controls}>
            <SegmentedControl
              value={hz}
              onChange={(v) => setHz(v as ForecastHorizon)}
              data={[
                { label: 'Court', value: 'short' },
                { label: 'Moyen', value: 'medium' },
                { label: 'Long', value: 'long' },
              ]}
              size="sm"
            />
            <Button
              variant="light"
              size="sm"
              onClick={exportCsv}
              aria-label="Exporter les prévisions en CSV"
              className={styles.primaryButton}
            >
              Exporter CSV
            </Button>
            <Button
              size="sm"
              onClick={() => refetch()}
              loading={isFetching}
              aria-label="Rafraîchir les prévisions"
              className={styles.primaryButton}
            >
              Rafraîchir
            </Button>
          </div>
        </div>

        {showSkeletons && (
          <div className={styles.skeletonGrid} aria-live="polite">
            {Array.from({ length: Math.min(6, Math.max(3, Math.ceil(limit / 2))) }).map((_, idx) => (
              <div key={`forecast-skeleton-${idx}`} className={styles.skeletonCard}>
                <Stack gap="sm">
                  <Skeleton height={12} width="40%" radius="xl" />
                  <Skeleton height={10} width="25%" radius="xl" />
                  <Skeleton height={48} radius="md" />
                  <Skeleton height={10} width="60%" radius="xl" />
                  <Skeleton height={10} width="45%" radius="xl" />
                </Stack>
              </div>
            ))}
          </div>
        )}

        {error && (
          <Alert
            title="Erreur"
            color="red"
            icon={<IconAlertCircle size={20} />}
            action={
              <Button
                size="xs"
                variant="light"
                onClick={() => refetch()}
                aria-label="Réessayer de charger les prévisions"
              >
                Réessayer
              </Button>
            }
          >
            <Text size="sm">Impossible de récupérer les prévisions</Text>
            <Text size="xs" c="dimmed" mt="xs">
              {String(error)}
            </Text>
          </Alert>
        )}

        {!isLoading && !error && !hasItems && (
          <div className={styles.emptyState}>
            <Group justify="center" gap="xs">
              <IconInfoCircle size={18} />
              <Text fw={600}>Aucune prévision disponible</Text>
            </Group>
            <Text size="sm" c="dimmed" mt={6}>
              Le moteur calcule de nouveaux signaux. Revenez dans quelques instants ou forcez un rafraîchissement.
            </Text>
            <Button size="xs" mt="sm" variant="light" onClick={() => refetch()}>
              Actualiser
            </Button>
          </div>
        )}

        {!isLoading && !error && hasItems && (
          <ScrollArea className={styles.scrollArea} type="auto" style={{ maxHeight: 420 }}>
            <div className={styles.forecastGrid}>
              {ensureArray(items).map((f) => {
                const trend = (f.direction || 'neutral').toLowerCase();
                return (
                  <MantineCard
                    key={`${f.ticker ?? f.symbol}-${f.horizon}`}
                    withBorder
                    shadow="sm"
                    padding="sm"
                    className={styles.forecastCard}
                    data-trend={trend}
                  >
                    <Stack gap="xs" style={{ flex: 1 }}>
                      <Group className={styles.cardHeader}>
                        <Group className={styles.tickerGroup}>
                          <Title
                            order={6}
                            className={styles.tickerTitle}
                            onClick={() => onSelectTicker?.(f.ticker ?? f.symbol ?? '')}
                            title="Ouvrir la page du ticker"
                          >
                            {f.ticker ?? f.symbol}
                          </Title>
                          <div className={styles.deltaIcon}>
                            <BadgeDelta deltaType={dirToDelta(f.direction)} size="xs" />
                          </div>
                        </Group>
                        <MantineBadge variant="light" size="xs" className={styles.horizonBadge}>
                          {f.horizon}
                        </MantineBadge>
                      </Group>

                      <Group className={styles.cardContent}>
                        <div className={styles.ringProgressWrapper}>
                          <RingProgress
                            size={52}
                            thickness={6}
                            sections={[
                              { value: f.score ?? 0, color: (f.score ?? 0) >= 66 ? 'green' : (f.score ?? 0) >= 33 ? 'yellow' : 'red' },
                            ]}
                            label={
                              <Tooltip label={`Score ${f.score ?? 0}/100`}>
                                <Text ta="center" fw={700} size="xs" style={{ cursor: 'help' }}>
                                  {f.score ?? 0}
                                </Text>
                              </Tooltip>
                            }
                          />
                        </div>
                        <Stack className={styles.metricsStack} gap={2}>
                          <div className={styles.metricItem}>
                            <Text className={styles.metricLabel}>Confiance</Text>
                            <Text className={`${styles.metricValue} ${getConfidenceColor(f.confidence)}`}>
                              {formatConfidence(f.confidence)}
                            </Text>
                          </div>
                          <div className={styles.metricItem}>
                            <Text className={styles.metricLabel}>ER attendu</Text>
                            <Text className={styles.metricValue}>
                              {(() => {
                                const erValue = f.expected_return_pct ?? f.expectedReturnPct ?? f.expected_return;
                                // Éviter les valeurs très proches de zéro qui donnent 0.00%
                                if (erValue === null || erValue === undefined || Math.abs(erValue) < 0.0001) {
                                  return <span className="text-gray-400">N/A</span>;
                                }
                                return formatPercent(erValue);
                              })()}
                            </Text>
                          </div>
                        </Stack>
                      </Group>

                      <Group className={styles.cardFooter}>
                        <MantineBadge
                          color={dirToBadge(f.direction).color}
                          size="sm"
                          variant="light"
                          className={styles.directionBadge}
                        >
                          {dirToBadge(f.direction).label}
                        </MantineBadge>
                        <Button
                          size="xs"
                          variant="light"
                          compact
                          className={styles.openButton}
                          onClick={() => handleOpenDetails(f)}
                        >
                          Ouvrir
                        </Button>
                      </Group>

                      {(f.forecasted_at ?? f.updatedAt) && (
                        <Text className={styles.timestamp} title={new Date(f.forecasted_at ?? f.updatedAt ?? '').toLocaleString()}>
                          MAJ {new Date(f.forecasted_at ?? f.updatedAt ?? '').toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}
                        </Text>
                      )}
                    </Stack>
                  </MantineCard>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </Stack>

      <ForecastDetailDrawer
        opened={drawerOpened}
        onClose={handleCloseDrawer}
        forecast={selectedForecast}
        onNavigateToTicker={handleNavigateToTicker}
      />
    </MantineCard>
  );
}
