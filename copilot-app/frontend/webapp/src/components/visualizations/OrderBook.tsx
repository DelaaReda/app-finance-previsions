/**
 * OrderBook - Visualisation du carnet d'ordres (bid/ask)
 * Trading professionnel niveau Bloomberg
 */

import { Card, Stack, Title, Text, Group, Badge, Tooltip } from '@mantine/core';
import { useMemo } from 'react';

interface OrderLevel {
  price: number;
  quantity: number;
  side: 'bid' | 'ask';
}

interface OrderBookProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Niveaux d'ordres */
  bids: Array<{ price: number; quantity: number }>;
  /** Niveaux d'ordres */
  asks: Array<{ price: number; quantity: number }>;
  /** Prix actuel */
  lastPrice?: number;
  /** Spread */
  spread?: number;
  /** Hauteur */
  height?: number;
}

export function OrderBook({
  title,
  description,
  bids,
  asks,
  lastPrice,
  spread,
  height = 500,
}: OrderBookProps) {
  const processedData = useMemo(() => {
    // Trier bids (décroissant) et asks (croissant)
    const sortedBids = [...bids].sort((a, b) => b.price - a.price);
    const sortedAsks = [...asks].sort((a, b) => a.price - b.price);
    
    const maxQuantity = Math.max(
      ...sortedBids.map(b => b.quantity),
      ...sortedAsks.map(a => a.quantity)
    );
    
    const bestBid = sortedBids[0]?.price || 0;
    const bestAsk = sortedAsks[0]?.price || 0;
    const midPrice = (bestBid + bestAsk) / 2;
    const calculatedSpread = bestAsk - bestBid;
    
    return {
      bids: sortedBids.map(b => ({
        ...b,
        normalizedQuantity: (b.quantity / maxQuantity) * 100,
        distanceFromMid: ((b.price - midPrice) / midPrice) * 100,
      })),
      asks: sortedAsks.map(a => ({
        ...a,
        normalizedQuantity: (a.quantity / maxQuantity) * 100,
        distanceFromMid: ((a.price - midPrice) / midPrice) * 100,
      })),
      bestBid,
      bestAsk,
      midPrice,
      spread: spread || calculatedSpread,
      maxQuantity,
    };
  }, [bids, asks, spread]);

  const { bids: processedBids, asks: processedAsks, bestBid, bestAsk, midPrice, spread: finalSpread } = processedData;

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        {/* Spread info */}
        <Group gap="lg">
          <div>
            <Text size="xs" c="dimmed">Best Bid</Text>
            <Text fw={700} size="lg" c="teal">${bestBid.toFixed(2)}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Best Ask</Text>
            <Text fw={700} size="lg" c="red">${bestAsk.toFixed(2)}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Spread</Text>
            <Text fw={700} size="lg" c="orange">${finalSpread.toFixed(2)}</Text>
          </div>
          {lastPrice && (
            <div>
              <Text size="xs" c="dimmed">Last Price</Text>
              <Text fw={700} size="lg" c={lastPrice >= midPrice ? 'teal' : 'red'}>
                ${lastPrice.toFixed(2)}
              </Text>
            </div>
          )}
        </Group>
        
        <div style={{ position: 'relative', height: `${height}px`, display: 'flex', flexDirection: 'column' }}>
          {/* Asks (top) */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column-reverse', gap: '2px' }}>
            {processedAsks.slice(0, 10).map((ask, index) => (
              <Tooltip
                key={index}
                label={
                  <div>
                    <Text size="sm" fw={600}>Ask ${ask.price.toFixed(2)}</Text>
                    <Text size="xs">Quantity: {ask.quantity.toLocaleString()}</Text>
                  </div>
                }
                withArrow
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    height: `${100 / 10}%`,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <div style={{ flex: 1, textAlign: 'right', paddingRight: '8px' }}>
                    <Text size="xs" c="dimmed">{ask.quantity.toLocaleString()}</Text>
                  </div>
                  <div style={{
                    width: `${ask.normalizedQuantity}%`,
                    height: '100%',
                    backgroundColor: '#ef4444',
                    opacity: 0.7,
                    borderRadius: '2px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingRight: '8px',
                  }}>
                    <Text size="xs" fw={600} c="white" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}>
                      ${ask.price.toFixed(2)}
                    </Text>
                  </div>
                </div>
              </Tooltip>
            ))}
          </div>
          
          {/* Mid price line */}
          <div style={{
            height: '2px',
            backgroundColor: 'var(--mantine-color-gray-6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '8px 0',
          }}>
            <Badge variant="light" size="sm">
              Mid: ${midPrice.toFixed(2)}
            </Badge>
          </div>
          
          {/* Bids (bottom) */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {processedBids.slice(0, 10).map((bid, index) => (
              <Tooltip
                key={index}
                label={
                  <div>
                    <Text size="sm" fw={600}>Bid ${bid.price.toFixed(2)}</Text>
                    <Text size="xs">Quantity: {bid.quantity.toLocaleString()}</Text>
                  </div>
                }
                withArrow
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    height: `${100 / 10}%`,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <div style={{
                    width: `${bid.normalizedQuantity}%`,
                    height: '100%',
                    backgroundColor: '#10b981',
                    opacity: 0.7,
                    borderRadius: '2px',
                    display: 'flex',
                    alignItems: 'center',
                    paddingLeft: '8px',
                  }}>
                    <Text size="xs" fw={600} c="white" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}>
                      ${bid.price.toFixed(2)}
                    </Text>
                  </div>
                  <div style={{ flex: 1, textAlign: 'left', paddingLeft: '8px' }}>
                    <Text size="xs" c="dimmed">{bid.quantity.toLocaleString()}</Text>
                  </div>
                </div>
              </Tooltip>
            ))}
          </div>
        </div>
        
        {/* Legend */}
        <Group gap="lg" mt="md">
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#10b981', borderRadius: '2px', opacity: 0.7 }}></div>
            <Text size="xs">Bids (Achats)</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#ef4444', borderRadius: '2px', opacity: 0.7 }}></div>
            <Text size="xs">Asks (Ventes)</Text>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}

