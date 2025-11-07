/**
 * Macro Widget for Dashboard
 * Displays real macro economic indicators
 */

import { Card, Stack, Title, Text, SimpleGrid, Badge, Group, Skeleton, Alert } from '@mantine/core';
import { IconChartLine, IconInfoCircle, IconTrendingUp, IconTrendingDown } from '@tabler/icons-react';
import { RingProgress } from '@mantine/core';
import { useApi } from '@/hooks/useApi';

export function MacroWidget() {
  const { data, isLoading, error } = useApi<any>('/api/macro/series'); // Use series endpoint that actually works as verified by curl
  
  // Process the macro data - from curl we know it returns inflation_yoy, yield_curve_slope, unemployment, recession_prob
  let macroValues = {};
  if (data) {
    // Handle both direct data and nested data
    const actualData = data.data || data;
    if (actualData) {
      macroValues = actualData;
    }
  }

  // Define indicators based on actual API response structure
  const indicators = [
    {
      id: 'inflation_yoy',
      rawId: 'inflation_yoy',
      name: 'Inflation YoY',
      value: macroValues['inflation_yoy'] || macroValues['inflation'] || null,
      unit: '%',
      description: 'Year-over-year consumer price changes'
    },
    {
      id: 'unemployment_rate',
      rawId: 'unemployment',
      name: 'Unemployment Rate',
      value: macroValues['unemployment'] || macroValues['unemployment_rate'] || null,
      unit: '%',
      description: 'Current unemployment rate'
    },
    {
      id: 'yield_curve',
      rawId: 'yield_curve_slope',
      name: 'Yield Curve',
      value: macroValues['yield_curve_slope'] || macroValues['yield'] || null,
      unit: '',
      description: '10Y-2Y Treasury spread'
    },
    {
      id: 'recession_prob',
      rawId: 'recession_prob',
      name: 'Recession Prob',
      value: macroValues['recession_prob'] ? macroValues['recession_prob'] * 100 : null, // Convert to percentage
      unit: '%',
      description: 'Model-estimated probability'
    }
  ].filter(indicator => indicator.value !== null && indicator.value !== undefined);

  // Function to determine status and color based on value and indicator type
  const getStatusInfo = (id: string, value: number) => {
    if (value === null || value === undefined) {
      return { status: 'no data', color: 'gray' };
    }
    
    switch (id) {
      case 'inflation_yoy':
        if (value < 2.5) return { status: 'low', color: 'green' };
        if (value < 3.5) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      case 'unemployment_rate':
        if (value < 4.0) return { status: 'low', color: 'green' };
        if (value < 5.0) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      case 'yield_curve':
        if (value > 0.5) return { status: 'positive', color: 'green' };
        if (value > 0) return { status: 'neutral', color: 'yellow' };
        return { status: 'inverted', color: 'red' };
      case 'recession_prob':
        if (value < 30) return { status: 'low', color: 'green' };
        if (value < 50) return { status: 'moderate', color: 'yellow' };
        return { status: 'high', color: 'red' };
      default:
        return { status: 'neutral', color: 'gray' };
    }
  };

  return (
    <Card padding="lg" shadow="sm" withBorder>
      <Stack gap="md">
        <Group gap="xs">
          <IconChartLine size={24} color="#3B82F6" />
          <Title order={4}>Macro Indicators</Title>
        </Group>

        {isLoading && (
          <Stack gap="md">
            {[...Array(4)].map((_, i) => (
              <Card key={i} withBorder padding="md">
                <Stack gap="xs" align="center">
                  <Skeleton height={10} width="60%" />
                  <Skeleton height={60} circle />
                  <Skeleton height={8} width="40%" />
                </Stack>
              </Card>
            ))}
          </Stack>
        )}

        {error && (
          <Alert color="red" variant="light" title="Data Error">
            <Text size="sm">Failed to load macro data: {error}</Text>
          </Alert>
        )}

        {!isLoading && !error && indicators.length > 0 && (
          <SimpleGrid cols={{ base: 2, md: 4 }} spacing="md">
            {indicators.map((indicator) => {
              const statusInfo = getStatusInfo(indicator.id, indicator.value as number);
              
              // Calculate progress value (0-100) for ring display
              let progressValue = 0;
              if (indicator.id === 'recession_prob') {
                progressValue = Math.min(100, Math.abs(indicator.value as number));
              } else {
                progressValue = Math.min(100, Math.abs(indicator.value as number) * 10); // Scale other values
              }
              
              return (
                <Card key={indicator.id} withBorder padding="md" radius="md">
                  <Stack gap="xs" align="center">
                    <Text size="xs" c="dimmed" ta="center" fw={500}>{indicator.name}</Text>
                    <RingProgress
                      size={70}
                      thickness={7}
                      sections={[{ value: progressValue, color: statusInfo.color }]}
                      label={
                        <Text ta="center" fw={700} size="sm">
                          {(indicator.value as number).toFixed(2)}{indicator.unit}
                        </Text>
                      }
                    />
                    <Group gap={4} justify="center">
                      {typeof indicator.value === 'number' && indicator.value > 0 && indicator.id !== 'recession_prob' && (
                        <IconTrendingUp size={12} color={statusInfo.color} />
                      )}
                      {typeof indicator.value === 'number' && indicator.value < 0 && indicator.id !== 'recession_prob' && (
                        <IconTrendingDown size={12} color={statusInfo.color} />
                      )}
                      <Badge size="xs" color={statusInfo.color} variant="light">
                        {statusInfo.status}
                      </Badge>
                    </Group>
                    <Text size="xs" c="dimmed" ta="center">{indicator.description}</Text>
                  </Stack>
                </Card>
              );
            })}
          </SimpleGrid>
        )}

        {!isLoading && !error && indicators.length === 0 && (
          <Text size="sm" c="dimmed" ta="center">
            No macro data available
          </Text>
        )}
      </Stack>
    </Card>
  );
}
