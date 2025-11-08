/**
 * Trading Page - OrderBook Visualization
 * Real-time orderbook data for trading analysis
 * Author: AUTO-FULLSTACK-DEVELOPER-SPIDERMAN-77
 */
import { Container, Stack, Select, Skeleton, Group } from '@mantine/core'
import { IconChartBar, IconRefresh } from '@tabler/icons-react'
import PageHeader from '@/components/layout/PageHeader'
import { OrderBook } from '@/components/visualizations'
import { useOrderBook } from '@/hooks/useOrderBook'
import EmptyState from '@/components/ui/EmptyState'
import { useState } from 'react'
import { Button } from '@mantine/core'

const DEFAULT_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL', 'META', 'AMZN', 'SPY', 'QQQ']

export default function Trading() {
  const [selectedTicker, setSelectedTicker] = useState('AAPL')
  const { data, isLoading, error, refetch } = useOrderBook(selectedTicker, true)

  return (
    <Container size="xl" py="xl">
      <PageHeader
        title="Trading - Carnet d'Ordres"
        icon={<IconChartBar size={28} />}
        description="Visualisation du carnet d'ordres en temps réel"
        actions={
          <Group gap="md">
            <Select
              label="Ticker"
              placeholder="Sélectionner un ticker"
              value={selectedTicker}
              onChange={(value) => value && setSelectedTicker(value)}
              data={DEFAULT_TICKERS.map(t => ({ value: t, label: t }))}
              style={{ minWidth: 150 }}
            />
            <Button
              variant="light"
              onClick={() => refetch()}
              leftSection={<IconRefresh size={16} />}
            >
              Rafraîchir
            </Button>
          </Group>
        }
      />

      <Stack gap="xl" mt="xl">
        {isLoading ? (
          <Skeleton height={600} radius="md" />
        ) : error ? (
          <EmptyState
            icon={<IconChartBar size={48} />}
            title="Erreur de chargement"
            description={error instanceof Error ? error.message : "Impossible de charger le carnet d'ordres"}
            action={{
              label: "Réessayer",
              onClick: () => refetch()
            }}
          />
        ) : data && data.bids.length > 0 && data.asks.length > 0 ? (
          <OrderBook
            title={`Carnet d'Ordres - ${data.ticker}`}
            bids={data.bids}
            asks={data.asks}
            lastPrice={data.lastPrice}
          />
        ) : (
          <EmptyState
            icon={<IconChartBar size={48} />}
            title="Aucune donnée disponible"
            description={`Le carnet d'ordres pour ${selectedTicker} sera disponible une fois les données chargées`}
            action={{
              label: "Rafraîchir",
              onClick: () => refetch()
            }}
          />
        )}
      </Stack>
    </Container>
  )
}

