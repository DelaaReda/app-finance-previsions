/**
 * RadarChart - Graphique radar pour scores multi-dimensionnels
 * Parfait pour scores composite (Macro, Technique, News, etc.)
 */

import { Card, Stack, Title, Text } from '@mantine/core';
import {
  RadarChart as ReRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

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
  const palette = colors.length > 0 ? colors : ['#4c6ef5', '#0ca678', '#ff922b', '#f03e3e'];

  const formatValue = (value: any) => {
    if (typeof value === 'number') {
      return value.toFixed(1);
    }
    return String(value);
  };

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ height: 360 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ReRadarChart data={data}>
              <PolarGrid stroke="#334155" strokeDasharray="4 4" />
              <PolarAngleAxis
                dataKey={index}
                tick={{ fill: '#94a3b8', fontSize: 12 }}
              />
              <PolarRadiusAxis
                tickFormatter={formatValue}
                stroke="#475569"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
              />
              {categories.map((category, idx) => {
                const color = palette[idx % palette.length];
                return (
                  <Radar
                    key={category}
                    name={category}
                    dataKey={category}
                    stroke={color}
                    fill={color}
                    fillOpacity={0.2}
                    strokeWidth={2}
                  />
                );
              })}
              <Legend wrapperStyle={{ paddingTop: 12 }} />
              <Tooltip formatter={(value) => formatValue(value)} />
            </ReRadarChart>
          </ResponsiveContainer>
        </div>
      </Stack>
    </Card>
  );
}
