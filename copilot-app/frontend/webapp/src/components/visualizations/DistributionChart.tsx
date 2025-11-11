/**
 * DistributionChart - Distribution de valeurs (histogramme)
 * Pour scores, rendements, volatilités, etc.
 */

import { Card, Stack, Title, Text, Group } from '@mantine/core';
import { BarChart } from '@tremor/react';

interface DistributionChartProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données (bins avec counts) */
  data: Array<{
    bin: string; // Ex: "0-10", "10-20", etc.
    count: number;
    label?: string;
  }>;
  /** Couleur */
  color?: string;
  /** Format de label */
  labelFormatter?: (bin: string) => string;
}

export function DistributionChart({
  title,
  description,
  data,
  color = 'blue',
  labelFormatter = (bin) => bin,
}: DistributionChartProps) {
  const chartData = data.map(d => ({
    bin: labelFormatter(d.bin),
    Count: d.count,
  }));

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
          <BarChart
            data={chartData}
            index="bin"
            categories={['Count']}
            colors={[color]}
            showLegend={false}
            showGridLines
            showAnimation
            valueFormatter={(value) => value.toString()}
          />
        </div>
        
        {/* Stats */}
        <Group gap="lg" mt="md">
          <div>
            <Text size="xs" c="dimmed">Total</Text>
            <Text fw={600}>{data.reduce((sum, d) => sum + d.count, 0)}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Moyenne</Text>
            <Text fw={600}>
              {data.length > 0 
                ? (data.reduce((sum, d) => sum + d.count, 0) / data.length).toFixed(1)
                : '0'}
            </Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Max</Text>
            <Text fw={600}>{Math.max(...data.map(d => d.count))}</Text>
          </div>
        </Group>
      </Stack>
    </Card>
  );
}

