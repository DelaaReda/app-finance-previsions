import { Card, Text } from '@mantine/core';
import { BarList } from '@tremor/react';

export function BarListWidget({
  title,
  items,
  height = 300,
  empty,
  loading,
}: {
  title?: string;
  items: { name: string; value: number }[];
  height?: number;
  empty?: boolean;
  loading?: boolean;
}) {
  return (
    <Card withBorder shadow="sm" data-testid="bar-list">
      {title && (
        <Text fw={600} mb="xs">
          {title}
        </Text>
      )}
      {empty && !loading ? <Text c="dimmed">Aucune donnée</Text> : <div style={{ height }}><BarList data={items} /></div>}
    </Card>
  );
}
