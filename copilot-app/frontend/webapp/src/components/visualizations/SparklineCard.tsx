/**
 * SparklineCard - Mini graphique sparkline dans une card
 * Style Bloomberg Terminal pour tendances rapides
 */

import { Card, Stack, Group, Text, Badge } from '@mantine/core';
import { LineChart } from '@tremor/react';
import type { ReactNode } from 'react';

interface SparklineCardProps {
  /** Label */
  label: string;
  /** Valeur actuelle */
  value: string | number;
  /** Variation */
  change?: number;
  /** Données pour sparkline */
  data: Array<{ date: string; value: number }>;
  /** Couleur */
  color?: string;
  /** Icône */
  icon?: ReactNode;
  /** Badge optionnel */
  badge?: {
    label: string;
    color: string;
  };
}

export function SparklineCard({
  label,
  value,
  change,
  data,
  color = 'blue',
  icon,
  badge,
}: SparklineCardProps) {
  const isPositive = change !== undefined && change >= 0;
  
  return (
    <Card padding="md" radius="md" withBorder style={{ height: '100%' }}>
      <Stack gap="sm" style={{ height: '100%' }}>
        <Group justify="space-between" align="flex-start">
          <div style={{ flex: 1 }}>
            <Group gap="xs" align="center" mb={4}>
              {icon && <div>{icon}</div>}
              <Text size="sm" c="dimmed" fw={500}>
                {label}
              </Text>
              {badge && (
                <Badge color={badge.color} variant="light" size="xs">
                  {badge.label}
                </Badge>
              )}
            </Group>
            <Group gap="xs" align="baseline" mb={4}>
              <Text size="xl" fw={700}>
                {typeof value === 'number' ? value.toLocaleString() : value}
              </Text>
              {change !== undefined && (
                <Badge
                  color={isPositive ? 'teal' : 'red'}
                  variant="light"
                  size="sm"
                >
                  {isPositive ? '+' : ''}{change.toFixed(2)}%
                </Badge>
              )}
            </Group>
          </div>
        </Group>

        {/* Sparkline */}
        {data.length > 0 && (
          <div style={{ height: 60, marginTop: 'auto' }}>
            <LineChart
              data={data}
              index="date"
              categories={['value']}
              colors={[color]}
              showLegend={false}
              showGridLines={false}
              showXAxis={false}
              showYAxis={false}
              curveType="natural"
              connectNulls
            />
          </div>
        )}
      </Stack>
    </Card>
  );
}

