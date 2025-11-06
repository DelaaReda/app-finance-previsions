import { Badge, Group, Tooltip } from '@mantine/core';
import { Card } from '@/ui';
import { useHealth } from '@/hooks/useHealth';

export default function HealthBar() {
  const { data } = useHealth();

  const datasets = data?.datasets ?? [];

  return (
    <Card data-testid="health-bar">
      <Group gap="xs">
        {datasets.map((dataset) => {
          const threshold = data?.thresholds?.stale_sec?.[dataset.name] ?? 3600;
          const stale = dataset.latency_sec > threshold;
          const color = stale ? 'red' : dataset.errors_24h > 0 ? 'yellow' : 'green';
          const tooltip = `${dataset.name}: ${dataset.latency_sec}s latency, ${dataset.errors_24h} errors/24h`;
          return (
            <Tooltip key={dataset.name} label={tooltip} openDelay={200}>
              <Badge color={color}>{dataset.name}</Badge>
            </Tooltip>
          );
        })}
      </Group>
    </Card>
  );
}
