import { Card, Text } from '@mantine/core';
import { LineChart } from '@tremor/react';

export function LineChartWidget({
  title,
  data,
  index,
  categories,
  height = 260,
  loading,
  empty,
}: {
  title?: string;
  data: any[];
  index: string;
  categories: string[];
  height?: number;
  loading?: boolean;
  empty?: boolean;
}) {
  return (
    <Card withBorder shadow="sm" data-testid="line-chart">
      {title && (
        <Text fw={600} mb="xs">
          {title}
        </Text>
      )}
      {empty && !loading ? (
        <Text c="dimmed">Aucune donnée</Text>
      ) : (
        <div style={{ height }}>
          <LineChart data={data} index={index} categories={categories} yAxisWidth={50} showAnimation={!loading} />
        </div>
      )}
    </Card>
  );
}
