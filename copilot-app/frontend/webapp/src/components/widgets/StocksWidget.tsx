/**
 * Stocks Widget for Dashboard
 * Displays real stock data and top movers
 */

import { Card, Stack, Title, Text, Table, Badge, Group, Skeleton, Alert, ActionIcon } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconRefresh } from '@tabler/icons-react';
import { useApi } from '@/hooks/useApi';

interface StockData {
  ticker: string;
  name?: string;
  current_price?: number;
  price_change_pct?: number;
  volume?: string;
  market_cap?: string;
}

export function StocksWidget() {
  const { data, isLoading, error, refetch } = useApi<any>('/api/stocks/top?limit=10');

  // Process the stock data - with top endpoint, we get a list of stocks
  let topStocks: StockData[] = [];
  if (data && data.data && data.data.stocks) {
    // New format: { ok: true, data: { stocks: [...] } }
    topStocks = data.data.stocks;
  } else if (data && data.stocks) {
    // Direct format: { stocks: [...] }
    topStocks = data.stocks;
  } else if (data && Array.isArray(data)) {
    // Array format
    topStocks = data;
  }

  return (
    <Card padding="lg" shadow="sm" withBorder>
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={4}>Top Stocks</Title>
          <ActionIcon 
            size="sm" 
            variant="light" 
            color="blue" 
            onClick={() => refetch()} 
            loading={isLoading}
            aria-label="Actualiser les données des actions"
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </Group>

        {isLoading && (
          <Table>
            <Table.Tbody>
              {[...Array(5)].map((_, i) => (
                <Table.Tr key={i}>
                  <Table.Td><Skeleton height={16} width="40px" /></Table.Td>
                  <Table.Td><Skeleton height={16} width="60px" /></Table.Td>
                  <Table.Td><Skeleton height={16} width="50px" /></Table.Td>
                  <Table.Td><Skeleton height={16} width="60px" /></Table.Td>
                  <Table.Td><Skeleton height={16} width="50px" /></Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}

        {error && (
          <Alert color="red" variant="light" title="Data Error">
            <Text size="sm">Failed to load stock data: {error}</Text>
          </Alert>
        )}

        {!isLoading && !error && topStocks.length > 0 && (
          <Table striped highlightOnHover withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Ticker</Table.Th>
                <Table.Th>Name</Table.Th>
                <Table.Th>Price</Table.Th>
                <Table.Th>Change</Table.Th>
                <Table.Th>Market Cap</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {topStocks.map((stock: any, index: number) => {
                // Extract data from the top stocks response structure
                const ticker = stock.ticker || stock.symbol || stock.id || `STK${index+1}`;
                const name = stock.name || stock.company_name || ticker;
                const price = stock.price || stock.current_price || 0;
                const change = stock.change || stock.price_change || 0;
                const changePercent = stock.change_percent || stock.price_change_pct || 0;
                const marketCap = stock.market_cap || stock.mcap || 0;
                
                // Format price with proper decimal places
                const formattedPrice = typeof price === 'number' && price > 0 ? `$${price.toFixed(2)}` : '—';
                
                // Format change properly - avoid NaN
                let formattedChange = '—';
                if (typeof changePercent === 'number' && !isNaN(changePercent) && isFinite(changePercent)) {
                  formattedChange = `${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
                } else if (typeof change === 'number' && !isNaN(change) && isFinite(change) && price > 0) {
                  const calculatedPercent = (change / price) * 100;
                  if (!isNaN(calculatedPercent) && isFinite(calculatedPercent)) {
                    formattedChange = `${calculatedPercent > 0 ? '+' : ''}${calculatedPercent.toFixed(2)}%`;
                  }
                }
                
                // Format market cap
                let formattedMarketCap = '—';
                if (typeof marketCap === 'number' && marketCap > 0) {
                  if (marketCap >= 1e9) {
                    formattedMarketCap = `$${(marketCap / 1e9).toFixed(2)}B`;
                  } else if (marketCap >= 1e6) {
                    formattedMarketCap = `$${(marketCap / 1e6).toFixed(2)}M`;
                  } else if (marketCap >= 1e3) {
                    formattedMarketCap = `$${(marketCap / 1e3).toFixed(2)}K`;
                  } else {
                    formattedMarketCap = `$${marketCap.toFixed(0)}`;
                  }
                }

                return (
                  <Table.Tr key={ticker}>
                    <Table.Td>
                      <Text fw={600} size="sm">{ticker}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">{name}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Text fw={500} c={price > 0 ? 'blue.7' : undefined} size="sm">
                        {formattedPrice}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} justify="left">
                        {formattedChange !== '—' && (
                          <>
                            {(changePercent > 0 || change > 0) ? (
                              <IconTrendingUp size={14} color="green" />
                            ) : (changePercent < 0 || change < 0) ? (
                              <IconTrendingDown size={14} color="red" />
                            ) : null}
                          </>
                        )}
                        <Badge 
                          size="sm"
                          color={
                            formattedChange === '—' ? 'gray' :
                            (changePercent > 0 || change > 0) ? 'green' : 
                            (changePercent < 0 || change < 0) ? 'red' : 'gray'
                          } 
                          variant="light"
                        >
                          {formattedChange}
                        </Badge>
                      </Group>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm" c="dimmed">
                        {formattedMarketCap}
                      </Text>
                    </Table.Td>
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
        )}

        {!isLoading && !error && topStocks.length === 0 && (
          <Text size="sm" c="dimmed" ta="center">
            No stock data available
          </Text>
        )}
      </Stack>
    </Card>
  );
}
