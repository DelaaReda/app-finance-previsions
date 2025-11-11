/**
 * CandlestickChart - Graphique chandelier japonais
 * Essentiel pour trading technique
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo } from 'react';

interface CandlestickData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface CandlestickChartProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données OHLCV */
  data: CandlestickData[];
  /** Ticker */
  ticker?: string;
  /** Hauteur */
  height?: number;
}

export function CandlestickChart({
  title,
  description,
  data,
  ticker,
  height = 400,
}: CandlestickChartProps) {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));
    const maxPrice = Math.max(...sorted.map(d => d.high));
    const minPrice = Math.min(...sorted.map(d => d.low));
    const priceRange = maxPrice - minPrice;
    
    return sorted.map(d => {
      const isBullish = d.close >= d.open;
      const bodyTop = Math.max(d.open, d.close);
      const bodyBottom = Math.min(d.open, d.close);
      const bodyHeight = bodyTop - bodyBottom;
      const wickTop = d.high;
      const wickBottom = d.low;
      
      // Normaliser pour affichage (0-100%)
      const normalize = (price: number) => ((price - minPrice) / priceRange) * 100;
      
      return {
        ...d,
        isBullish,
        bodyTop: normalize(bodyTop),
        bodyBottom: normalize(bodyBottom),
        bodyHeight: normalize(bodyHeight) || 0.5, // Min 0.5% pour visibilité
        wickTop: normalize(wickTop),
        wickBottom: normalize(wickBottom),
        bodyCenter: normalize((d.open + d.close) / 2),
      };
    });
  }, [data]);

  if (processedData.length === 0) {
    return (
      <Card padding="lg" radius="md" withBorder>
        <Text c="dimmed">Aucune donnée disponible</Text>
      </Card>
    );
  }

  const maxPrice = Math.max(...data.map(d => d.high));
  const minPrice = Math.min(...data.map(d => d.low));
  const barWidth = 100 / processedData.length;

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
          {ticker && (
            <Badge variant="light" mt={4}>{ticker}</Badge>
          )}
        </div>
        
        <div style={{ position: 'relative', height: `${height}px`, width: '100%' }}>
          {/* Y-axis labels */}
          <div style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: '50px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '8px 0',
          }}>
            {[maxPrice, (maxPrice + minPrice) / 2, minPrice].map((price, i) => (
              <Text key={i} size="xs" c="dimmed" style={{ transform: 'translateY(-50%)' }}>
                ${price.toFixed(2)}
              </Text>
            ))}
          </div>
          
          {/* Chart area */}
          <div style={{
            marginLeft: '60px',
            height: '100%',
            position: 'relative',
            borderLeft: '1px solid var(--mantine-color-gray-6)',
            borderBottom: '1px solid var(--mantine-color-gray-6)',
          }}>
            {processedData.map((candle, index) => {
              const left = (index / processedData.length) * 100;
              const color = candle.isBullish ? '#10b981' : '#ef4444';
              
              return (
                <Tooltip
                  key={index}
                  label={
                    <div>
                      <Text size="sm" fw={600}>{candle.date}</Text>
                      <Text size="xs">O: ${candle.open.toFixed(2)}</Text>
                      <Text size="xs">H: ${candle.high.toFixed(2)}</Text>
                      <Text size="xs">L: ${candle.low.toFixed(2)}</Text>
                      <Text size="xs">C: ${candle.close.toFixed(2)}</Text>
                      {candle.volume && (
                        <Text size="xs">V: {candle.volume.toLocaleString()}</Text>
                      )}
                    </div>
                  }
                  withArrow
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: `${left}%`,
                      width: `${barWidth * 0.6}%`,
                      height: '100%',
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'flex-end',
                      cursor: 'pointer',
                    }}
                  >
                    {/* Wick */}
                    <div
                      style={{
                        width: '2px',
                        height: `${candle.wickTop - candle.wickBottom}%`,
                        backgroundColor: color,
                        position: 'absolute',
                        bottom: `${candle.wickBottom}%`,
                      }}
                    />
                    
                    {/* Body */}
                    <div
                      style={{
                        width: '100%',
                        height: `${Math.max(candle.bodyHeight, 0.5)}%`,
                        backgroundColor: color,
                        position: 'absolute',
                        bottom: `${candle.bodyBottom}%`,
                        borderRadius: '2px',
                        border: `1px solid ${color}`,
                        opacity: 0.9,
                      }}
                    />
                  </div>
                </Tooltip>
              );
            })}
          </div>
        </div>
        
        {/* Legend */}
        <Group gap="lg" mt="md">
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#10b981', borderRadius: '2px' }}></div>
            <Text size="xs">Hausse</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#ef4444', borderRadius: '2px' }}></div>
            <Text size="xs">Baisse</Text>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}

