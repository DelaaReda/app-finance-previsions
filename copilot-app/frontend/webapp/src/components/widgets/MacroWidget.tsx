/**
 * Simple Macro Widget for Dashboard
 * Displays macro economic indicators
 */

import { Card, Stack, Title, Text, SimpleGrid, Badge, Group } from '@mantine/core';
import { IconChartLine } from '@tabler/icons-react';
import { RingProgress } from '@mantine/core';

export function MacroWidget() {
  // Mock macro data for now - can be connected to real endpoint later
  const macroIndicators = [
    { name: 'GDP Growth', value: 2.4, unit: '%', status: 'positive' },
    { name: 'Inflation Rate', value: 3.2, unit: '%', status: 'neutral' },
    { name: 'Unemployment', value: 4.1, unit: '%', status: 'positive' },
    { name: 'Interest Rate', value: 5.25, unit: '%', status: 'neutral' },
  ];

  const getStatusColor = (status: string) => {
    if (status === 'positive') return 'green';
    if (status === 'negative') return 'red';
    return 'yellow';
  };

  return (
    <Card padding="lg">
      <Stack gap="md">
        <Group gap="xs">
          <IconChartLine size={24} color="#4169E1" />
          <Title order={4}>Macro Indicators</Title>
        </Group>

        <SimpleGrid cols={{ base: 2, md: 4 }} spacing="md">
          {macroIndicators.map((indicator) => (
            <Card key={indicator.name} withBorder padding="md">
              <Stack gap="xs" align="center">
                <Text size="xs" c="dimmed" ta="center">{indicator.name}</Text>
                <RingProgress
                  size={60}
                  thickness={6}
                  sections={[{ value: (indicator.value / 10) * 100, color: getStatusColor(indicator.status) }]}
                  label={
                    <Text ta="center" fw={700} size="sm">
                      {indicator.value}
                      <Text size="xs" c="dimmed" component="span">{indicator.unit}</Text>
                    </Text>
                  }
                />
                <Badge size="xs" color={getStatusColor(indicator.status)}>
                  {indicator.status}
                </Badge>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>

        <Text size="xs" c="dimmed" ta="center">
          Mock data - Connect to real macro endpoint for live data
        </Text>
      </Stack>
    </Card>
  );
}
