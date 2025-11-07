/**
 * RiskMatrix - Matrice de risque/rendement
 * Visualisation professionnelle pour allocation portfolio
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { ScatterChart } from '@tremor/react';
import type { ReactNode } from 'react';

interface RiskMatrixProps {
  /** Titre */
  title?: string;
  /** Description */
  description?: string;
  /** Données (risk, return, ticker) */
  data: Array<{
    ticker: string;
    risk: number; // 0-100
    return: number; // -100 à +100
    category?: string;
    size?: number; // Pour taille du point
  }>;
  /** Légende personnalisée */
  legend?: ReactNode;
}

export function RiskMatrix({
  title = 'Matrice Risque/Rendement',
  description,
  data,
  legend,
}: RiskMatrixProps) {
  // Transformer les données pour ScatterChart
  const chartData = data.map(d => ({
    ticker: d.ticker,
    Risk: d.risk,
    Return: d.return,
    category: d.category || 'default',
    size: d.size || 1,
  }));

  // Quadrants
  const quadrants = [
    { label: 'Haut Rendement / Bas Risque', x: 0, y: 50, color: 'teal' },
    { label: 'Haut Rendement / Haut Risque', x: 50, y: 50, color: 'orange' },
    { label: 'Bas Rendement / Bas Risque', x: 0, y: 0, color: 'blue' },
    { label: 'Bas Rendement / Haut Risque', x: 50, y: 0, color: 'red' },
  ];

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
        
        <div style={{ height: 400, position: 'relative' }}>
          <ScatterChart
            data={chartData}
            category="category"
            x="Risk"
            y="Return"
            size="size"
            showLegend={false}
            showGridLines
            showAnimation
            valueFormatter={(value) => `${value.toFixed(1)}%`}
          />
          
          {/* Quadrants overlay */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            pointerEvents: 'none',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gridTemplateRows: '1fr 1fr',
            opacity: 0.1,
          }}>
            {quadrants.map((q, i) => (
              <div
                key={i}
                style={{
                  backgroundColor: `var(--mantine-color-${q.color}-6)`,
                  border: `2px dashed var(--mantine-color-${q.color}-4)`,
                }}
              />
            ))}
          </div>
        </div>
        
        {/* Quadrants legend */}
        <Group gap="lg" mt="md">
          {quadrants.map((q, i) => (
            <Group key={i} gap="xs">
              <div style={{
                width: 16,
                height: 16,
                backgroundColor: `var(--mantine-color-${q.color}-6)`,
                borderRadius: '4px',
                border: `1px solid var(--mantine-color-${q.color}-4)`,
              }} />
              <Text size="xs">{q.label}</Text>
            </Group>
          ))}
        </Group>
      </Stack>
    </Card>
  );
}

