/**
 * CorrelationHeatmap - Heatmap de corrélations entre tickers
 * Visualisation professionnelle pour identifier les corrélations de marché
 */

import { Card, Stack, Title, Text, Group, Tooltip } from '@mantine/core';
import { useMemo } from 'react';

interface CorrelationHeatmapProps {
  /** Données de corrélation */
  data: Array<{
    ticker1: string;
    ticker2: string;
    correlation: number; // -1 à 1
  }>;
  /** Tickers uniques à afficher */
  tickers: string[];
  /** Titre */
  title?: string;
  /** Description */
  description?: string;
}

export function CorrelationHeatmap({
  data,
  tickers,
  title = 'Matrice de Corrélation',
  description,
}: CorrelationHeatmapProps) {
  // Créer une matrice de corrélation
  const matrix = useMemo(() => {
    const matrix: Record<string, Record<string, number>> = {};
    
    tickers.forEach(t1 => {
      matrix[t1] = {};
      tickers.forEach(t2 => {
        if (t1 === t2) {
          matrix[t1][t2] = 1;
        } else {
          const correlation = data.find(
            d => (d.ticker1 === t1 && d.ticker2 === t2) || (d.ticker1 === t2 && d.ticker2 === t1)
          )?.correlation ?? 0;
          matrix[t1][t2] = correlation;
        }
      });
    });
    
    return matrix;
  }, [data, tickers]);

  const getColor = (value: number) => {
    if (value >= 0.7) return '#10b981'; // Teal - Forte corrélation positive
    if (value >= 0.3) return '#34d399'; // Teal light
    if (value >= -0.3) return '#6b7280'; // Gray - Neutre
    if (value >= -0.7) return '#f87171'; // Red light
    return '#ef4444'; // Red - Forte corrélation négative
  };

  const getIntensity = (value: number) => {
    return Math.abs(value) * 100;
  };

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ overflowX: 'auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: `auto repeat(${tickers.length}, 80px)`, gap: '4px' }}>
            {/* Header row */}
            <div></div>
            {tickers.map(ticker => (
              <div key={ticker} style={{ 
                writingMode: 'vertical-rl', 
                textOrientation: 'mixed',
                fontSize: '11px',
                fontWeight: 600,
                padding: '8px 4px',
                textAlign: 'center'
              }}>
                {ticker}
              </div>
            ))}
            
            {/* Data rows */}
            {tickers.map(ticker1 => (
              <div key={ticker1} style={{ display: 'contents' }}>
                <div style={{ 
                  fontSize: '11px', 
                  fontWeight: 600, 
                  padding: '8px',
                  display: 'flex',
                  alignItems: 'center'
                }}>
                  {ticker1}
                </div>
                {tickers.map(ticker2 => {
                  const value = matrix[ticker1]?.[ticker2] ?? 0;
                  const color = getColor(value);
                  const intensity = getIntensity(value);
                  
                  return (
                    <Tooltip
                      key={`${ticker1}-${ticker2}`}
                      label={`${ticker1} ↔ ${ticker2}: ${(value * 100).toFixed(1)}%`}
                      withArrow
                    >
                      <div
                        style={{
                          backgroundColor: color,
                          opacity: Math.max(0.3, intensity / 100),
                          minHeight: '40px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          cursor: 'pointer',
                          borderRadius: '4px',
                          transition: 'transform 0.2s',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'scale(1.1)';
                          e.currentTarget.style.zIndex = '10';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'scale(1)';
                          e.currentTarget.style.zIndex = '1';
                        }}
                      >
                        <Text size="xs" fw={700} c="white" style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}>
                          {(value * 100).toFixed(0)}%
                        </Text>
                      </div>
                    </Tooltip>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        
        {/* Legend */}
        <Group gap="md" mt="md">
          <Group gap="xs">
            <div style={{ width: 20, height: 20, backgroundColor: '#10b981', borderRadius: '4px' }}></div>
            <Text size="xs">Forte corrélation (+)</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 20, backgroundColor: '#6b7280', borderRadius: '4px' }}></div>
            <Text size="xs">Neutre</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 20, backgroundColor: '#ef4444', borderRadius: '4px' }}></div>
            <Text size="xs">Forte corrélation (-)</Text>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}

