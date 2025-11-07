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
  
  // Create mock data for now using the known structure
  const macroSeries: MacroSeries[] = [
    {
      id: 'cpi',
      name: 'Inflation YoY',
      description: 'Year-over-year consumer price changes',
      current_value: 3.02,
      unit: '%',
      points: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: 3.02 + (Math.random() - 0.5) * 0.2
      }))
    },
    {
      id: 'unemployment',
      name: 'Unemployment Rate',
      description: 'Current unemployment rate',
      current_value: 4.3,
      unit: '%',
      points: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: 4.3 + (Math.random() - 0.5) * 0.1
      }))
    },
    {
      id: 'yield_curve',
      name: 'Yield Curve',
      description: '10Y-2Y Treasury spread',
      current_value: 0.53,
      unit: '',
      points: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: 0.53 + (Math.random() - 0.5) * 0.1
      }))
    },
    {
      id: 'recession_prob',
      name: 'Recession Probability',
      description: 'Model-estimated probability',
      current_value: 29.47,
      unit: '%',
      points: Array.from({ length: 30 }, (_, i) => ({
        date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        value: 29.47 + (Math.random() - 0.5) * 5
      }))
    }
  ];

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
                    <Text size="lg" fw={700}>{series.current_value.toFixed(2)}{series.unit}</Text>
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
                      valueFormatter={(value) => `${value?.toFixed(1) ?? '0'}${series.unit}`}
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