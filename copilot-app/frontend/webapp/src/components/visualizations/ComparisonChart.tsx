/**
 * ComparisonChart - Graphique de comparaison
 * Compare plusieurs séries avec visualisation claire
 */

import { Card, Stack, Title, Text, Group, Badge } from '@mantine/core';
import { AreaChart, BarChart, LineChart } from '@tremor/react';
import type { ReactNode } from 'react';

interface ComparisonChartProps {
  /** Titre du graphique */
  title: string;
  /** Description */
  description?: string;
  /** Données */
  data: Array<Record<string, any>>;
  /** Catégories à afficher */
  categories: string[];
  /** Index (colonne pour l'axe X) */
  index: string;
  /** Type de graphique */
  type?: 'area' | 'bar' | 'line';
  /** Couleurs pour chaque catégorie */
  colors?: string[];
  /** Légende personnalisée */
  legend?: ReactNode;
  /** Hauteur */
  height?: number;
}

export function ComparisonChart({
  title,
  description,
  data,
  categories,
  index,
  type = 'area',
  colors = ['blue', 'teal', 'orange', 'red'],
  legend,
  height = 300,
}: ComparisonChartProps) {
  const ChartComponent = type === 'area' 
    ? AreaChart 
    : type === 'bar' 
    ? BarChart 
    : LineChart;

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={4} mb={4}>{title}</Title>
            {description && (
              <Text size="sm" c="dimmed">{description}</Text>
            )}
          </div>
          {legend && <div>{legend}</div>}
        </Group>
        
        <div style={{ height }}>
          <ChartComponent
            data={data}
            index={index}
            categories={categories}
            colors={colors}
            valueFormatter={(value) => {
              if (typeof value === 'number') {
                return value.toLocaleString();
              }
              return String(value);
            }}
            showLegend={!legend}
            showGridLines
            showAnimation
          />
        </div>
      </Stack>
    </Card>
  );
}

