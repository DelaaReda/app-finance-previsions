/**
 * RadarChart - Graphique radar pour scores multi-dimensionnels
 * Parfait pour scores composite (Macro, Technique, News, etc.)
 */

import { Card, Stack, Title, Text, Group } from '@mantine/core';
import { RadarChart as TremorRadar } from '@tremor/react';

interface RadarChartProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données (une série par ticker/entité) */
  data: Array<Record<string, any>>;
  /** Catégories à afficher (axes du radar) */
  categories: string[];
  /** Index (colonne pour identifier chaque point) */
  index: string;
  /** Couleurs */
  colors?: string[];
}

export function RadarChart({
  title,
  description,
  data,
  categories,
  index,
  colors = ['blue', 'teal', 'orange', 'red'],
}: RadarChartProps) {
  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ height: 350 }}>
          <TremorRadar
            data={data}
            index={index}
            categories={categories}
            colors={colors}
            valueFormatter={(value) => {
              if (typeof value === 'number') {
                return value.toFixed(1);
              }
              return String(value);
            }}
            showLegend
            showGridLines
            showAnimation
          />
        </div>
      </Stack>
    </Card>
  );
}

