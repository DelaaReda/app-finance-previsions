import { Card, Text } from '@mantine/core';
import { AreaChart } from '@tremor/react';

export function AreaChartWidget({
  title,
  data,
  index,
  categories,
  height = 260,
  empty,
  loading,
}: {
  title?: string;
  data: any[];
  index: string;
  categories: string[];
  height?: number;
  empty?: boolean;
  loading?: boolean;
}) {
  return (
    <Card withBorder shadow="sm" data-testid="area-chart">
      {title && (
        <Text fw={600} mb="xs">
          {title}
        </Text>
      )}
      {empty && !loading ? (
        <Text c="dimmed">Aucune donnée</Text>
      ) : (
        <div style={{ height }}>
          <AreaChart data={data} index={index} categories={categories} yAxisWidth={50} showAnimation={!loading} />
        </div>
      )}
    </Card>
  );
}
