/**
 * ForecastCardsWidget Component
 * Displays forecast cards with scores and confidence measures
 */

import { useState, useMemo } from 'react';
import { 
  Grid, 
  Group, 
  Alert, 
  SegmentedControl, 
  Tooltip, 
  ActionIcon, 
  Button, 
  Card as MantineCard, 
  Title, 
  Text, 
  RingProgress,
  Badge as MantineBadge,
  ScrollArea,
  Stack
} from '@mantine/core';
import { IconLoader, IconAlertCircle, IconInfoCircle } from '@tabler/icons-react';
import { BadgeDelta } from '@tremor/react';
import { useForecasts } from '@/hooks/useForecasts';
import type { ForecastHorizon } from '@/types/forecast';
import { ensureArray, safeGet } from '@/lib/safe';
import { ForecastDetailDrawer } from '@/components/forecasts/ForecastDetailDrawer';
import { useNavigate } from 'react-router-dom';
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

  return (
    <MantineCard padding="lg" className={styles.forecastContainer}>
      <Stack gap="md" style={{ flex: 1, minHeight: 0 }}>
        <Group justify="space-between" align="center" wrap="wrap" gap="sm">
          <div>
            <Title order={4}>{title}</Title>
            <Text c="dimmed" size="sm" mt={4}>Classement par score et confiance • Horizon: {hz}</Text>
          </div>
          <Group gap="xs" wrap="wrap">
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
            >
              Exporter CSV
            </Button>
            <Button 
              size="sm" 
              onClick={() => refetch()} 
              loading={isFetching}
              aria-label="Rafraîchir les prévisions"
            >
              Rafraîchir
            </Button>
          </Group>
        </Group>

      {isLoading && (
        <Alert 
          title="Chargement" 
          color="blue" 
          icon={<IconLoader size={20} />}
        >
          <Text size="sm">Récupération des prévisions en cours…</Text>
        </Alert>
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
          <Text size="xs" c="dimmed" mt="xs">{String(error)}</Text>
        </Alert>
      )}
      {!isLoading && !error && ensureArray(items).length === 0 && (
        <Alert 
          color="yellow"
          icon={<IconInfoCircle size={20} />}
          action={
            <Button 
              size="xs" 
              variant="light" 
              onClick={() => refetch()}
              aria-label="Réessayer de charger les prévisions"
            >
              Actualiser
            </Button>
          }
        >
          <Text size="sm">Aucune prévision disponible pour l'univers sélectionné.</Text>
          <Text size="xs" c="dimmed" mt="xs">
            Le système calcule les prévisions en arrière-plan. Réessayez dans quelques instants.
          </Text>
        </Alert>
      )}

        {!isLoading && !error && ensureArray(items).length > 0 && (
          <ScrollArea className={styles.scrollArea} type="auto">
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
                            size={60}
                            thickness={8}
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
                            <Text className={styles.metricValue}>{Math.round((f.confidence ?? 0) * 100)}%</Text>
                          </div>
                          <div className={styles.metricItem}>
                            <Text className={styles.metricLabel}>ER attendu</Text>
                            <Text className={styles.metricValue}>{fmtPct((f.expected_return_pct ?? f.expectedReturnPct ?? 0) / 100)}</Text>
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
      
      {/* Forecast Detail Drawer */}
      <ForecastDetailDrawer
        opened={drawerOpened}
        onClose={handleCloseDrawer}
        forecast={selectedForecast}
        onNavigateToTicker={handleNavigateToTicker}
      />
    </MantineCard>
  );
}
