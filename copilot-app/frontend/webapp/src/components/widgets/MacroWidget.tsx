/**
 * Macro Widget for Dashboard
 * Displays real macro economic indicators
 */

import { Card, Stack, Title, Text, SimpleGrid, Badge, Group, Skeleton, Alert, Button, ActionIcon } from '@mantine/core';
import { IconChartLine, IconInfoCircle, IconTrendingUp, IconTrendingDown, IconRefresh } from '@tabler/icons-react';
import { RingProgress } from '@mantine/core';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';
import { useApi } from '@/hooks/useApi';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import styles from './MacroWidget.module.css';

export function MacroWidget() {
  const { data, isLoading, error, refetch } = useApi<any>('/api/macro/series');

  // Process the macro data from series format
  // API returns: { ok: true, data: { series: [{ id, name, unit, frequency, points: [{date, value}] }] } }
  // OR: { data: { series: [...] } } (direct format)
  // OR: { series: [...] } (flat format)
  let macroValues: Record<string, number> = {};
  if (data) {
    // Handle different response formats
    let actualData: any = data;
    
    // If data has a 'data' property, use it
    if (data.data && typeof data.data === 'object') {
      actualData = data.data;
    }
    
    // Extract series array - handle multiple possible formats
    let series: any[] = [];
    
    if (Array.isArray(actualData)) {
      // If actualData is directly an array, use it
      series = actualData;
    } else if (actualData && typeof actualData === 'object') {
      // Try different possible keys for series
      if (Array.isArray(actualData.series)) {
        series = actualData.series;
      } else if (Array.isArray(actualData.data)) {
        series = actualData.data;
      } else if (Array.isArray(actualData.payload)) {
        series = actualData.payload;
      }
    }
    
    // Ensure series is an array before iterating
    if (!Array.isArray(series)) {
      console.warn('[MacroWidget] series is not an array:', series, 'data:', data);
      series = [];
    }

    // Extract latest value from each series
    series.forEach((s: any) => {
      if (s && typeof s === 'object') {
        // Handle different point formats
        let points: any[] = [];
        
        if (Array.isArray(s.points)) {
          points = s.points;
        } else if (Array.isArray(s.data)) {
          points = s.data;
        }
        
        if (points.length > 0) {
          // Get the last point (most recent)
          const lastPoint = points[points.length - 1];
          
          // Extract value from different possible formats
          const value = lastPoint?.value ?? lastPoint?.[1] ?? lastPoint?.level ?? lastPoint?.close ?? null;
          const seriesId = s.id ?? s.series_id ?? s.name ?? null;
          
          if (seriesId && value !== null && value !== undefined) {
            macroValues[seriesId] = value;
          }
        }
      }
    });
  }

  // Map series IDs to display indicators
  const seriesMapping = {
    'CPIAUCSL': { name: 'CPI', unit: 'index', description: 'Consumer Price Index', id: 'inflation' },
    'UNRATE': { name: 'Unemployment', unit: '%', description: 'Unemployment Rate', id: 'unemployment' },
    'DGS10': { name: '10Y Treasury', unit: '%', description: '10-Year Treasury Yield', id: 'treasury_10y' },
    'DGS2': { name: '2Y Treasury', unit: '%', description: '2-Year Treasury Yield', id: 'treasury_2y' },
    'VIXCLS': { name: 'VIX', unit: '', description: 'Market Volatility Index', id: 'vix' },
  };

  // Build indicators from available series
  const indicators = Object.entries(macroValues)
    .map(([seriesId, value]) => {
      const mapping = seriesMapping[seriesId as keyof typeof seriesMapping];
      if (!mapping) return null;

      return {
        id: mapping.id,
        rawId: seriesId,
        name: mapping.name,
        value: value,
        unit: mapping.unit,
        description: mapping.description
      };
    })
    .filter((indicator): indicator is NonNullable<typeof indicator> => indicator !== null);

  // Function to determine status and color based on value and indicator type
  const getStatusInfo = (id: string, value: number) => {
    if (value === null || value === undefined) {
      return { status: 'no data', color: 'gray' };
    }

    switch (id) {
      case 'inflation':
        // CPI index values - showing latest value
        if (value < 250) return { status: 'low', color: 'green' };
        if (value < 300) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      case 'unemployment':
        if (value < 4.0) return { status: 'low', color: 'green' };
        if (value < 5.0) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      case 'treasury_10y':
      case 'treasury_2y':
        // Treasury yields in percentage
        if (value < 3.0) return { status: 'low', color: 'green' };
        if (value < 5.0) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      case 'vix':
        // VIX volatility index
        if (value < 15) return { status: 'low', color: 'green' };
        if (value < 25) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      default:
        return { status: 'neutral', color: 'gray' };
    }
  };

  return (
    <Card padding="lg" radius="xl" className={`${sharedStyles.glassCard} ${styles.widgetCard}`}>
      <Stack gap="md">
        <Group justify="space-between" align="center">
          <Group gap="xs">
            <IconChartLine size={24} color="#3B82F6" />
            <div>
              <Title order={4}>Indicateurs Macroéconomiques</Title>
              {data?.data?.last_updated || data?.last_updated ? (
                <Text size="xs" c="dimmed" mt={4}>
                  Dernière mise à jour: {formatDistanceToNow(new Date(data?.data?.last_updated || data?.last_updated), { addSuffix: true, locale: fr })}
                </Text>
              ) : null}
            </div>
          </Group>
          <ActionIcon 
            size="sm" 
            variant="light" 
            color="blue" 
            onClick={() => refetch()} 
            loading={isLoading}
            aria-label="Rafraîchir les données macro"
            className={sharedStyles.actionIcon}
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </Group>

        {isLoading && (
          <SimpleGrid cols={{ base: 2, md: 4 }} spacing="md">
            {[...Array(4)].map((_, i) => (
              <Card key={i} padding="md" radius="lg" className={`${sharedStyles.skeletonCard} ${styles.indicatorSkeleton}`}>
                <Stack gap="sm" align="center">
                  <Skeleton height={12} width="60%" radius="xl" />
                  <Skeleton height={60} circle />
                  <Skeleton height={10} width="40%" radius="xl" />
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}

        {error && (
          <Alert 
            color="red" 
            variant="light" 
            title="Erreur de données"
            action={
              <Button size="xs" variant="light" onClick={() => window.location.reload()}>
                Réessayer
              </Button>
            }
          >
            <Text size="sm">Échec du chargement des données macro: {error}</Text>
            <Text size="xs" c="dimmed" mt="xs">
              Les données macroéconomiques sont temporairement indisponibles. Veuillez réessayer dans quelques instants.
            </Text>
          </Alert>
        )}

        {!isLoading && !error && indicators.length > 0 && (
          <SimpleGrid cols={{ base: 2, sm: 3, md: 5 }} spacing="md">
            {indicators.map((indicator) => {
              const statusInfo = getStatusInfo(indicator.id, indicator.value as number);

              // Calculate progress value (0-100) for ring display
              let progressValue = 0;
              const val = indicator.value as number;

              switch (indicator.id) {
                case 'inflation':
                  // CPI index: normalize around 200-320 range
                  progressValue = Math.min(100, Math.max(0, ((val - 200) / 120) * 100));
                  break;
                case 'unemployment':
                  // Unemployment rate: scale 0-10% range
                  progressValue = Math.min(100, (val / 10) * 100);
                  break;
                case 'treasury_10y':
                case 'treasury_2y':
                  // Treasury yields: scale 0-8% range
                  progressValue = Math.min(100, (val / 8) * 100);
                  break;
                case 'vix':
                  // VIX: scale 0-50 range
                  progressValue = Math.min(100, (val / 50) * 100);
                  break;
                default:
                  progressValue = Math.min(100, Math.abs(val));
              }

              return (
                <Card key={indicator.id} padding="md" radius="lg" className={`${sharedStyles.flatCard} ${styles.indicatorCard}`}>
                  <Stack gap="xs" align="center">
                    <Text size="xs" c="dimmed" ta="center" fw={500}>{indicator.name}</Text>
                    <RingProgress
                      size={60}
                      thickness={6}
                      sections={[{ value: progressValue, color: statusInfo.color }]}
                      label={
                        <Text ta="center" fw={700} size="sm">
                          {indicator.id === 'inflation'
                            ? (indicator.value as number).toFixed(1)
                            : (indicator.value as number).toFixed(2)}{indicator.unit}
                        </Text>
                      }
                    />
                      <Group gap={4} justify="center">
                        <Badge size="xs" color={statusInfo.color} variant="light">
                          {statusInfo.status}
                      </Badge>
                    </Group>
                    
                  </Stack>
                </Card>
              );
            })}
          </SimpleGrid>
        )}

        {!isLoading && !error && indicators.length === 0 && (
          <Alert 
            color="yellow" 
            variant="light" 
            title="Aucune donnée macro disponible"
            icon={<IconInfoCircle size={20} />}
            action={
              <Button 
                size="xs" 
                variant="light" 
                onClick={() => refetch()}
                aria-label="Actualiser les données macroéconomiques"
              >
                Actualiser
              </Button>
            }
          >
            <Text size="sm">
              Les données macroéconomiques ne sont pas encore disponibles. Le système récupère les données depuis FRED en arrière-plan.
            </Text>
            <Text size="xs" c="dimmed" mt="xs">
              Les indicateurs macro (CPI, Unemployment, Treasury Yields) seront affichés une fois les données chargées.
            </Text>
          </Alert>
        )}
      </Stack>
    </Card>
  );
}
