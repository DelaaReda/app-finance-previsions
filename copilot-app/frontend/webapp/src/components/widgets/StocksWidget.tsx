/**
 * Stocks Widget for Dashboard
 * Displays real stock data and top movers
 */

import { Card, Stack, Title, Text, Table, Badge, Group, Skeleton, ActionIcon, ScrollArea, Button, Alert } from '@mantine/core';
import { IconTrendingUp, IconTrendingDown, IconRefresh, IconChartBar } from '@tabler/icons-react';
import { useApi } from '@/hooks/useApi';
import { formatCurrency, formatPercent, getChangeColor } from '@/lib/formatting';
import sharedStyles from '@/shared/styles/widgets/glassWidget.module.css';
import styles from './StocksWidget.module.css';
import ErrorAlert from '@/components/ui/ErrorAlert';

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

  const isEmpty = !isLoading && !error && topStocks.length === 0;
  const allZeroChange = !isLoading && !error && topStocks.length > 0 && topStocks.every((s: any) => {
    const p = s.change_percent ?? s.price_change_pct ?? 0;
    const c = s.change ?? 0;
    return (!p || Math.abs(p) < 0.001) && (!c || Math.abs(c) < 0.001);
  });

  return (
    <Card padding="lg" radius="xl" className={`${sharedStyles.glassCard} ${styles.widgetCard}`}>
      <Stack gap="md">
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            <div className={sharedStyles.sparkIcon}>
              <IconChartBar size={18} />
            </div>
            <div>
              <Title order={4}>Top Stocks</Title>
              <Text size="xs" className={styles.subtitle}>
                Classement des dix meilleures actions suivies en temps réel
              </Text>
            </div>
          </div>
          <ActionIcon
            size="sm"
            variant="light"
            color="blue"
            onClick={() => refetch()}
            loading={isLoading}
            aria-label="Actualiser les données des actions"
            className={sharedStyles.actionIcon}
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </div>

        {isLoading && (
          <div className={`${styles.tableWrapper} ${styles.skeletonTable}`}>
            <Table>
              <Table.Tbody>
                {Array.from({ length: 5 }).map((_, i) => (
                  <Table.Tr key={`stock-skeleton-${i}`}>
                    <Table.Td><Skeleton height={14} width="48px" /></Table.Td>
                    <Table.Td><Skeleton height={14} width="80px" /></Table.Td>
                    <Table.Td><Skeleton height={14} width="60px" /></Table.Td>
                    <Table.Td><Skeleton height={14} width="70px" /></Table.Td>
                    <Table.Td><Skeleton height={14} width="80px" /></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </div>
        )}

        {error && (
          <ErrorAlert
            title="Données indisponibles"
            message="Impossible de charger les actions en temps réel."
            error={error}
            onReload={() => refetch()}
          />
        )}

        {!isLoading && !error && topStocks.length > 0 && (
          <ScrollArea className={styles.tableWrapper} type="auto">
            <Table highlightOnHover className={styles.table}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Ticker</Table.Th>
                  <Table.Th>Nom</Table.Th>
                  <Table.Th>Prix</Table.Th>
                  <Table.Th>Variation</Table.Th>
                  {!topStocks.every((s: any) => !s.market_cap && !s.mcap) && (
                    <Table.Th>Capitalisation</Table.Th>
                  )}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {topStocks.map((stock: any, index: number) => {
                  // Extract data from the top stocks response structure
                  const ticker = stock.ticker || stock.symbol || stock.id || `STK${index + 1}`;
                  const name = stock.name || stock.company_name || ticker;
                  const price = stock.price || stock.current_price || 0;
                  const change = stock.change || stock.price_change || 0;
                  const changePercent = stock.change_percent || stock.price_change_pct || 0;
                  const marketCap = stock.market_cap || stock.mcap || 0;

                  const formattedPrice = formatCurrency(price, 'USD');

                  let formattedChange = 'N/A';
                  let changeValue = 0;
                  
                  if (typeof changePercent === 'number' && Number.isFinite(changePercent) && Math.abs(changePercent) >= 0.01) {
                    // Si le pourcentage est fourni et significatif (>=0.01%)
                    changeValue = changePercent;
                    formattedChange = formatPercent(changePercent / 100);
                  } else if (typeof change === 'number' && Number.isFinite(change) && price > 0) {
                    // Calculer le pourcentage depuis le changement absolu
                    const calculatedPercent = (change / price) * 100;
                    if (Number.isFinite(calculatedPercent) && Math.abs(calculatedPercent) >= 0.01) {
                      changeValue = calculatedPercent;
                      formattedChange = formatPercent(calculatedPercent / 100);
                    }
                  }

                  const formattedMarketCap = formatCurrency(marketCap, 'USD', true);

                  return (
                    <Table.Tr key={ticker}>
                      <Table.Td>
                        <Text className={styles.tickerCell}>{ticker}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm" className={styles.name}>{name}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text fw={600} size="sm" className={styles.price}>
                          {formattedPrice}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={6} justify="left">
                          {formattedChange !== 'N/A' && changeValue !== 0 && (
                            changeValue > 0 ? (
                              <IconTrendingUp size={14} color="#16a34a" />
                            ) : changeValue < 0 ? (
                              <IconTrendingDown size={14} color="#dc2626" />
                            ) : null
                          )}
                          <Badge
                            size="sm"
                            radius="sm"
                            variant="light"
                            color={
                              formattedChange === 'N/A'
                                ? 'gray'
                                : changeValue > 0
                                  ? 'green'
                                  : changeValue < 0
                                    ? 'red'
                                    : 'gray'
                            }
                          >
                            {formattedChange}
                          </Badge>
                        </Group>
                      </Table.Td>
                      {!topStocks.every((s: any) => !s.market_cap && !s.mcap) && (
                        <Table.Td>
                          <Text size="sm" className={styles.marketCap}>
                            {formattedMarketCap}
                          </Text>
                        </Table.Td>
                      )}
                  </Table.Tr>
                );
              })}
            </Table.Tbody>
          </Table>
          </ScrollArea>
        )}

        {!isLoading && !error && allZeroChange && (
          <Alert color="gray" variant="light" mt="xs">
            <Text size="xs" c="dimmed">Marché fermé ou données statiques — variations indisponibles pour l’instant.</Text>
          </Alert>
        )}

        {isEmpty && (
          <div className={styles.emptyState}>
            <Text fw={600}>Aucune donnée d'actions disponible</Text>
            <Text size="sm" c="dimmed" mt={6}>
              Les données seront rechargées dès qu'un flux valide sera détecté.
            </Text>
          </div>
        )}
      </Stack>
    </Card>
  );
}
