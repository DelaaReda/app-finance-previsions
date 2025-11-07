/**
 * VolumeProfile - Profil de volume (POC, VAH, VAL)
 * Trading technique avancé
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo } from 'react';

interface VolumeProfileData {
  price: number;
  volume: number;
}

interface VolumeProfileProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données volume par prix */
  data: VolumeProfileData[];
  /** Prix actuel */
  currentPrice?: number;
  /** Hauteur */
  height?: number;
}

export function VolumeProfile({
  title,
  description,
  data,
  currentPrice,
  height = 400,
}: VolumeProfileProps) {
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    const sorted = [...data].sort((a, b) => a.price - b.price);
    const maxVolume = Math.max(...sorted.map(d => d.volume));
    const minPrice = Math.min(...sorted.map(d => d.price));
    const maxPrice = Math.max(...sorted.map(d => d.price));
    const priceRange = maxPrice - minPrice;
    
    // Trouver POC (Point of Control - prix avec plus de volume)
    const poc = sorted.reduce((max, d) => d.volume > max.volume ? d : max, sorted[0]);
    
    // Calculer VAH (Value Area High) et VAL (Value Area Low)
    // Value Area = 70% du volume total
    const totalVolume = sorted.reduce((sum, d) => sum + d.volume, 0);
    const valueAreaVolume = totalVolume * 0.7;
    
    let accumulatedVolume = 0;
    let vah = maxPrice;
    let val = minPrice;
    
    // Trouver VAH (en partant du haut)
    for (let i = sorted.length - 1; i >= 0; i--) {
      accumulatedVolume += sorted[i].volume;
      if (accumulatedVolume >= valueAreaVolume / 2) {
        vah = sorted[i].price;
        break;
      }
    }
    
    // Trouver VAL (en partant du bas)
    accumulatedVolume = 0;
    for (let i = 0; i < sorted.length; i++) {
      accumulatedVolume += sorted[i].volume;
      if (accumulatedVolume >= valueAreaVolume / 2) {
        val = sorted[i].price;
        break;
      }
    }
    
    return {
      bars: sorted.map(d => ({
        ...d,
        normalizedPrice: ((d.price - minPrice) / priceRange) * 100,
        normalizedVolume: (d.volume / maxVolume) * 100,
      })),
      poc,
      vah,
      val,
      minPrice,
      maxPrice,
    };
  }, [data]);

  if (processedData.bars.length === 0) {
    return (
      <Card padding="lg" radius="md" withBorder>
        <Text c="dimmed">Aucune donnée disponible</Text>
      </Card>
    );
  }

  const { bars, poc, vah, val, minPrice, maxPrice } = processedData;
  const maxBarWidth = 60; // % of chart width

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ position: 'relative', height: `${height}px`, width: '100%' }}>
          {/* Y-axis (prices) */}
          <div style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: '60px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '8px 0',
          }}>
            <Text size="xs" c="dimmed">${maxPrice.toFixed(2)}</Text>
            <Text size="xs" c="dimmed">${((maxPrice + minPrice) / 2).toFixed(2)}</Text>
            <Text size="xs" c="dimmed">${minPrice.toFixed(2)}</Text>
          </div>
          
          {/* Chart area */}
          <div style={{
            marginLeft: '70px',
            height: '100%',
            position: 'relative',
            borderLeft: '1px solid var(--mantine-color-gray-6)',
            borderBottom: '1px solid var(--mantine-color-gray-6)',
          }}>
            {/* Value Area background */}
            <div
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                bottom: `${((val - minPrice) / (maxPrice - minPrice)) * 100}%`,
                height: `${((vah - val) / (maxPrice - minPrice)) * 100}%`,
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderTop: '1px dashed var(--mantine-color-blue-6)',
                borderBottom: '1px dashed var(--mantine-color-blue-6)',
              }}
            />
            
            {/* Volume bars */}
            {bars.map((bar, index) => {
              const isPOC = bar.price === poc.price;
              const isInValueArea = bar.price >= val && bar.price <= vah;
              const isCurrentPrice = currentPrice && Math.abs(bar.price - currentPrice) < 0.01;
              
              return (
                <Tooltip
                  key={index}
                  label={
                    <div>
                      <Text size="sm" fw={600}>${bar.price.toFixed(2)}</Text>
                      <Text size="xs">Volume: {bar.volume.toLocaleString()}</Text>
                      {isPOC && <Badge color="orange" size="xs" mt={4}>POC</Badge>}
                      {isInValueArea && <Badge color="blue" size="xs" mt={4}>Value Area</Badge>}
                    </div>
                  }
                  withArrow
                >
                  <div
                    style={{
                      position: 'absolute',
                      left: 0,
                      bottom: `${bar.normalizedPrice}%`,
                      width: `${(bar.normalizedVolume / 100) * maxBarWidth}%`,
                      height: `${100 / bars.length}%`,
                      backgroundColor: isPOC 
                        ? '#f59e0b' 
                        : isInValueArea 
                        ? '#3b82f6' 
                        : 'var(--mantine-color-gray-6)',
                      border: isPOC ? '2px solid #f59e0b' : '1px solid var(--mantine-color-gray-5)',
                      borderRadius: '2px',
                      cursor: 'pointer',
                      minWidth: '2px',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.opacity = '0.8';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.opacity = '1';
                    }}
                  />
                </Tooltip>
              );
            })}
            
            {/* Current price line */}
            {currentPrice && (
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  right: 0,
                  bottom: `${((currentPrice - minPrice) / (maxPrice - minPrice)) * 100}%`,
                  height: '2px',
                  backgroundColor: '#10b981',
                  zIndex: 10,
                }}
              >
                <div style={{
                  position: 'absolute',
                  right: '-60px',
                  top: '-8px',
                  backgroundColor: '#10b981',
                  color: 'white',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                }}>
                  ${currentPrice.toFixed(2)}
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Legend */}
        <Group gap="lg" mt="md">
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#f59e0b', borderRadius: '2px' }}></div>
            <Text size="xs">POC (Point of Control)</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#3b82f6', borderRadius: '2px', opacity: 0.3 }}></div>
            <Text size="xs">Value Area (70%)</Text>
          </Group>
          {currentPrice && (
            <Group gap="xs">
              <div style={{ width: 20, height: 2, backgroundColor: '#10b981' }}></div>
              <Text size="xs">Prix actuel</Text>
            </Group>
          )}
        </Group>
      </Stack>
    </Card>
  );
}

