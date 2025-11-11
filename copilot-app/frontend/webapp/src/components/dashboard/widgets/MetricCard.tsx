import { Card, Group, Stack, Text, Loader } from '@mantine/core';

export function MetricCard({
  title,
  value,
  hint,
  loading,
}: {
  title?: string;
  value?: string | number;
  hint?: string;
  loading?: boolean;
}) {
  return (
    <Card className="card" withBorder shadow="sm" data-testid="metric-card">
      <Stack gap="xs">
        {title && (
          <Text size="sm" c="dimmed">
            {title}
          </Text>
        )}
        <Group align="center" gap="xs">
          {loading ? <Loader size="sm" /> : <Text fz={28} fw={700}>{value ?? '—'}</Text>}
        </Group>
        {hint && (
          <Text size="xs" c="dimmed">
            {hint}
          </Text>
        )}
      </Stack>
    </Card>
  );
}
