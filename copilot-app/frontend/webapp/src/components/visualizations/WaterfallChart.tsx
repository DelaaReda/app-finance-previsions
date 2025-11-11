/**
 * WaterfallChart - Graphique en cascade pour P&L, cash flow, etc.
 * Style professionnel Bloomberg
 */

import { Card, Stack, Title, Text, Group } from '@mantine/core';
import { BarChart } from '@tremor/react';
import { useMemo } from 'react';

interface WaterfallDataPoint {
  label: string;
  value: number;
  type?: 'positive' | 'negative' | 'total';
}

interface WaterfallChartProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données */
  data: WaterfallDataPoint[];
  /** Format de valeur */
  valueFormatter?: (value: number) => string;
}

export function WaterfallChart({
  title,
  description,
  data,
  valueFormatter = (v) => v.toLocaleString(),
}: WaterfallChartProps) {
  // Transformer pour BarChart avec positions cumulatives
  const transformedData = useMemo(() => {
    let runningTotal = 0;
    return data.map((point, index) => {
      const isTotal = point.type === 'total';
      const start = isTotal ? 0 : runningTotal;
      const end = isTotal ? point.value : runningTotal + point.value;
      
      if (!isTotal) {
        runningTotal += point.value;
      }
      
      return {
        label: point.label,
        start,
        end,
        value: point.value,
        type: point.type || (point.value >= 0 ? 'positive' : 'negative'),
      };
    });
  }, [data]);

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ height: 300 }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', height: '100%', gap: '8px' }}>
            {transformedData.map((point, index) => {
              const isPositive = point.value >= 0;
              const height = Math.abs(point.value) / Math.max(...transformedData.map(d => Math.abs(d.value))) * 100;
              const color = point.type === 'total' 
                ? 'indigo' 
                : isPositive 
                ? 'teal' 
                : 'red';
              
              return (
                <div key={index} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div
                    style={{
                      width: '100%',
                      height: `${height}%`,
                      backgroundColor: `var(--mantine-color-${color}-6)`,
                      borderRadius: '4px 4px 0 0',
                      minHeight: '20px',
                      display: 'flex',
                      alignItems: 'flex-end',
                      justifyContent: 'center',
                      padding: '4px',
                    }}
                  >
                    <Text size="xs" fw={600} c="white" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}>
                      {isPositive ? '+' : ''}{valueFormatter(point.value)}
                    </Text>
                  </div>
                  <Text size="xs" c="dimmed" mt={4} ta="center" style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}>
                    {point.label}
                  </Text>
                </div>
              );
            })}
          </div>
        </div>
      </Stack>
    </Card>
  );
}

