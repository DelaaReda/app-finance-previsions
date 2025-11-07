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
  const { data, isLoading, error, refetch } = useApi<any>('/api/stocks/SPY/sheet');

  // Process the stock data - with sheet endpoint, we get a single stock's data
  let topStocks = [];
  if (data && data.data) {
    // With sheet endpoint, we get one stock's data in data.data
    topStocks = [data.data]; // Wrap single stock in array
  } else if (data && data.ticker) {
    // Direct response format
    topStocks = [data];
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
                // Extract data from the sheet response structure
                const ticker = stock.ticker || stock.symbol || stock.id || `STK${index+1}`;
                const name = stock.company_name || (stock.fundamentals && stock.fundamentals.name) || ticker;
                const price = stock.current_price || (stock.fundamentals && stock.fundamentals.price) || stock.price || 0;
                const priceChange = stock.price_change || (stock.fundamentals && stock.fundamentals.price_change) || 0;
                
                // Calculate percentage change from the raw price data
                let changePercent = 0;
                if (price && (stock.fundamentals?.price || price)) {
                  // Estimate percentage change based on price and change values
                  if (priceChange !== undefined && priceChange !== null && price && price !== priceChange) {
                    changePercent = (priceChange / (price - priceChange)) * 100;
                  }
                }
                
                // Format price with proper decimal places
                const formattedPrice = typeof price === 'number' ? `$${price.toFixed(2)}` : 'N/A';
                
                // Format change properly
                const formattedChange = typeof changePercent === 'number' ? 
                  `${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%` : 'N/A';
                
                const marketCap = stock.fundamentals?.market_cap;
                const formattedMarketCap = marketCap ? 
                  marketCap > 1e9 ? `$${(marketCap / 1e9).toFixed(2)}B` : 
                  marketCap > 1e6 ? `$${(marketCap / 1e6).toFixed(2)}M` : 
                  `$${marketCap}` : 'N/A';

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
                        {changePercent !== 0 && priceChange !== 0 && (
                          <>
                            {changePercent > 0 || priceChange > 0 ? (
                              <IconTrendingUp size={14} color="green" />
                            ) : (
                              <IconTrendingDown size={14} color="red" />
                            )}
                          </>
                        )}
                        <Badge 
                          size="sm"
                          color={changePercent > 0 || priceChange > 0 ? 'green' : 
                                changePercent < 0 || priceChange < 0 ? 'red' : 'gray'} 
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
