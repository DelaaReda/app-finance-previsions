/**
 * MetricCard - Card de métrique avec visualisation
 * Affiche une valeur avec tendance, icône et graphique mini
 */

import { Card, Stack, Group, Text, Badge, ThemeIcon } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconMinus } from '@tabler/icons-react';
import { LineChart } from '@tremor/react';
import type { ReactNode } from 'react';

interface MetricCardProps {
  /** Label de la métrique */
  label: string;
  /** Valeur principale */
  value: string | number;
  /** Variation (pourcentage) */
  change?: number;
  /** Icône optionnelle */
  icon?: ReactNode;
  /** Couleur du badge */
  color?: string;
  /** Données pour mini graphique */
  chartData?: Array<{ date: string; value: number }>;
  /** Description/tooltip */
  description?: string;
}

export function MetricCard({
  label,
  value,
  change,
  icon,
  color = 'blue',
  chartData,
  description,
}: MetricCardProps) {
  const isPositive = change !== undefined && change >= 0;
  const TrendIcon = change === undefined 
    ? IconMinus 
    : isPositive 
    ? IconTrendingUp 
    : IconTrendingDown;

  return (
    <Card padding="lg" radius="md" withBorder style={{ height: '100%' }}>
      <Stack gap="md" style={{ height: '100%' }}>
        <Group justify="space-between" align="flex-start">
          <div style={{ flex: 1 }}>
            <Text size="sm" c="dimmed" fw={500} mb={4}>
              {label}
            </Text>
            <Group gap="xs" align="baseline">
              <Text size="xl" fw={700}>
                {typeof value === 'number' ? value.toLocaleString() : value}
              </Text>
              {change !== undefined && (
                <Badge
                  color={isPositive ? 'teal' : 'red'}
                  variant="light"
                  leftSection={<TrendIcon size={12} />}
                >
                  {isPositive ? '+' : ''}{change.toFixed(2)}%
                </Badge>
              )}
            </Group>
            {description && (
              <Text size="xs" c="dimmed" mt={4}>
                {description}
              </Text>
            )}
          </div>
          {icon && (
            <ThemeIcon size={40} radius="md" variant="light" color={color}>
              {icon}
            </ThemeIcon>
          )}
        </Group>

        {chartData && chartData.length > 0 && (
          <div style={{ height: 60, marginTop: 'auto' }}>
            <LineChart
              data={chartData}
              index="date"
              categories={['value']}
              colors={[color]}
              showLegend={false}
              showGridLines={false}
              showXAxis={false}
              showYAxis={false}
              curveType="natural"
            />
          </div>
        )}
      </Stack>
    </Card>
  );
}

