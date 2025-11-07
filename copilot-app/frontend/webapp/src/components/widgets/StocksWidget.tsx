/**
 * Simple Stocks Widget for Dashboard
 * Displays stock screener/top movers
 */

import { Card, Stack, Title, Text, Table, Badge, Group, Button } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown } from '@tabler/icons-react';

export function StocksWidget() {
  // Mock stock data - can be connected to real endpoint later
  const topMovers = [
    { ticker: 'NVDA', name: 'NVIDIA', change: 5.2, price: 482.50, volume: '45.2M' },
    { ticker: 'TSLA', name: 'Tesla', change: -3.8, price: 242.18, volume: '98.1M' },
    { ticker: 'AAPL', name: 'Apple', change: 2.1, price: 178.92, volume: '52.3M' },
    { ticker: 'META', name: 'Meta', change: 1.9, price: 325.45, volume: '18.7M' },
    { ticker: 'AMZN', name: 'Amazon', change: -1.2, price: 142.78, volume: '42.5M' },
  ];

  return (
    <Card padding="lg">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={4}>Top Movers</Title>
          <Button size="xs" variant="light">View All</Button>
        </Group>

        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Ticker</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Price</Table.Th>
              <Table.Th>Change</Table.Th>
              <Table.Th>Volume</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {topMovers.map((stock) => (
              <Table.Tr key={stock.ticker}>
                <Table.Td>
                  <Text fw={600}>{stock.ticker}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">{stock.name}</Text>
                </Table.Td>
                <Table.Td>
                  <Text>${stock.price.toFixed(2)}</Text>
                </Table.Td>
                <Table.Td>
                  <Group gap={4}>
                    {stock.change > 0 ? (
                      <IconTrendingUp size={16} color="green" />
                    ) : (
                      <IconTrendingDown size={16} color="red" />
                    )}
                    <Badge color={stock.change > 0 ? 'green' : 'red'} variant="light">
                      {stock.change > 0 ? '+' : ''}{stock.change.toFixed(2)}%
                    </Badge>
                  </Group>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{stock.volume}</Text>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>

        <Text size="xs" c="dimmed" ta="center">
          Mock data - Connect to real stocks endpoint for live data
        </Text>
      </Stack>
    </Card>
  );
}
