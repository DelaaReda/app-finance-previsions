/**
 * Macro Sparklines Widget
 * Displays sparkline charts for key macro indicators (inflation, unemployment, etc.)
 */

import { Card, Stack, Title, Text, SimpleGrid, Group, Skeleton, Alert } from '@mantine/core';
import { AreaChart } from '@tremor/react';
import { IconChartLine } from '@tabler/icons-react';
import { useApi } from '@/hooks/useApi';

interface MacroPoint {
  date: string;
  value: number;
}

interface MacroSeries {
  id: string;
  name: string;
  description: string;
  points: MacroPoint[];
  current_value: number;
  unit: string;
}

export function MacroSparklinesWidget() {
  const { data, isLoading, error } = useApi<any>('/api/macro/series');

  // Parse real macro series data from API
  const macroSeries: MacroSeries[] = [];

  if (data) {
    const actualData = data.data || data;
    const series = actualData.series || [];

    // Series mapping for display
    const seriesMapping: Record<string, { name: string; description: string; unit: string }> = {
      'CPIAUCSL': {
        name: 'CPI Index',
        description: 'Consumer Price Index',
        unit: ''
      },
      'UNRATE': {
        name: 'Unemployment',
        description: 'Unemployment Rate',
        unit: '%'
      },
      'DGS10': {
        name: '10Y Treasury',
        description: '10-Year Treasury Yield',
        unit: '%'
      },
      'DGS2': {
        name: '2Y Treasury',
        description: '2-Year Treasury Yield',
        unit: '%'
      },
      'VIXCLS': {
        name: 'VIX Index',
        description: 'Market Volatility',
        unit: ''
      },
    };

    series.forEach((s: any) => {
      const mapping = seriesMapping[s.id];
      if (mapping && s.points && s.points.length > 0) {
        // Get last 90 points for sparkline (about 3 months)
        const recentPoints = s.points.slice(-90);
        const currentValue = recentPoints[recentPoints.length - 1].value;

        macroSeries.push({
          id: s.id,
          name: mapping.name,
          description: mapping.description,
          current_value: currentValue,
          unit: mapping.unit,
          points: recentPoints
        });
      }
    });
  }

  return (
    <Card padding="lg" shadow="sm" withBorder>
      <Stack gap="md">
        <Group gap="xs">
          <IconChartLine size={24} color="#3B82F6" />
          <Title order={4}>Macro Sparklines</Title>
        </Group>

        {isLoading && (
          <SimpleGrid cols={{ base: 1, md: 2, lg: 4 }} spacing="md">
            {Array.from({ length: 4 }).map((_, i) => (
              <Stack key={i} gap="xs">
                <Skeleton height={16} width="60%" />
                <Skeleton height={80} />
                <Skeleton height={12} width="40%" />
              </Stack>
            ))}
          </SimpleGrid>
        )}

        {error && (
          <Alert color="red" variant="light" title="Data Error">
            <Text size="sm">Failed to load macro data: {error}</Text>
          </Alert>
        )}

        {!isLoading && !error && (
          <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg">
            {macroSeries.map((series) => (
              <Card key={series.id} withBorder padding="md">
                <Stack gap="xs">
                  <Group justify="space-between" align="flex-start">
                    <div>
                      <Text size="sm" fw={600}>{series.name}</Text>
                      <Text size="xs" c="dimmed">{series.description}</Text>
                    </div>
                    <Text size="lg" fw={700}>
                      {series.id === 'CPIAUCSL'
                        ? series.current_value.toFixed(1)
                        : series.current_value.toFixed(2)}{series.unit}
                    </Text>
                  </Group>

                  <div style={{ height: '80px', marginTop: '8px' }}>
                    <AreaChart
                      className="h-full"
                      data={series.points}
                      index="date"
                      categories={['value']}
                      colors={['blue']}
                      showLegend={false}
                      showGridLines={false}
                      showYAxis={false}
                      showXAxis={false}
                      valueFormatter={(value) => {
                        if (series.id === 'CPIAUCSL') {
                          return `${value?.toFixed(1) ?? '0'}`;
                        }
                        return `${value?.toFixed(2) ?? '0'}${series.unit}`;
                      }}
                    />
                  </div>
                  
                  <Text size="xs" c="dimmed" ta="right">
                    {series.points.length > 0 ? 
                      `Du ${new Date(series.points[0].date).toLocaleDateString('fr-FR')} au ${new Date(series.points[series.points.length - 1].date).toLocaleDateString('fr-FR')}`
                     : 'Pas de données historiques'}
                  </Text>
                </Stack>
              </Card>
            ))}
          </SimpleGrid>
        )}

        {!isLoading && !error && macroSeries.length === 0 && (
          <Text size="sm" c="dimmed" ta="center">
            No macro series data available
          </Text>
        )}
      </Stack>
    </Card>
  );
}