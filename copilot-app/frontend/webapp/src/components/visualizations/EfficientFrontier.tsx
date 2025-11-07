/**
 * EfficientFrontier - Frontière efficiente (Portfolio Optimization)
 * Modern Portfolio Theory visualization
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { AreaChart } from '@tremor/react';
import { useMemo } from 'react';

interface PortfolioPoint {
  risk: number; // Volatilité (%)
  return: number; // Rendement attendu (%)
  sharpe?: number; // Ratio de Sharpe
  allocation?: Record<string, number>; // Allocation par ticker
}

interface EfficientFrontierProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Points de la frontière efficiente */
  frontier: PortfolioPoint[];
  /** Portfolios existants */
  portfolios?: Array<{
    name: string;
    risk: number;
    return: number;
    color?: string;
  }>;
  /** Hauteur */
  height?: number;
}

export function EfficientFrontier({
  title,
  description,
  frontier,
  portfolios = [],
  height = 400,
}: EfficientFrontierProps) {
  const chartData = useMemo(() => {
    return frontier.map(p => ({
      risk: p.risk.toFixed(2),
      'Frontière Efficiente': p.return,
      Sharpe: p.sharpe || 0,
    }));
  }, [frontier]);

  const maxRisk = Math.max(...frontier.map(p => p.risk));
  const maxReturn = Math.max(...frontier.map(p => p.return));
  const minRisk = Math.min(...frontier.map(p => p.risk));
  const minReturn = Math.min(...frontier.map(p => p.return));

  const formatValue = (value: number) => {
    return `${value.toFixed(2)}%`;
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
        
        <div style={{ height: `${height}px`, position: 'relative' }}>
          <AreaChart
            data={chartData}
            index="risk"
            categories={['Frontière Efficiente']}
            colors={['blue']}
            showLegend={false}
            showGridLines
            valueFormatter={formatValue}
            yAxisWidth={60}
          />
          
          {/* Overlay portfolios */}
          {portfolios.length > 0 && (
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              pointerEvents: 'none',
            }}>
              {portfolios.map((portfolio, index) => {
                const xPercent = ((portfolio.risk - minRisk) / (maxRisk - minRisk)) * 100;
                const yPercent = ((maxReturn - portfolio.return) / (maxReturn - minReturn)) * 100;
                
                return (
                  <Tooltip
                    key={index}
                    label={
                      <div>
                        <Text size="sm" fw={600}>{portfolio.name}</Text>
                        <Text size="xs">Risque: {portfolio.risk.toFixed(2)}%</Text>
                        <Text size="xs">Rendement: {portfolio.return.toFixed(2)}%</Text>
                      </div>
                    }
                    withArrow
                  >
                    <div
                      style={{
                        position: 'absolute',
                        left: `${xPercent}%`,
                        top: `${yPercent}%`,
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        backgroundColor: portfolio.color || '#f59e0b',
                        border: '2px solid white',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                        transform: 'translate(-50%, -50%)',
                        cursor: 'pointer',
                        pointerEvents: 'all',
                      }}
                    />
                  </Tooltip>
                );
              })}
            </div>
          )}
        </div>
        
        {/* Stats */}
        <Group gap="lg" mt="md">
          <div>
            <Text size="xs" c="dimmed">Risque Min</Text>
            <Text fw={600}>{minRisk.toFixed(2)}%</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Rendement Max</Text>
            <Text fw={600}>{maxReturn.toFixed(2)}%</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Points</Text>
            <Text fw={600}>{frontier.length}</Text>
          </div>
        </Group>
        
        {/* Legend */}
        <Group gap="lg" mt="md">
          <Group gap="xs">
            <div style={{ width: 20, height: 12, backgroundColor: '#3b82f6', borderRadius: '2px' }}></div>
            <Text size="xs">Frontière Efficiente</Text>
          </Group>
          {portfolios.length > 0 && (
            <Group gap="xs">
              <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#f59e0b', border: '2px solid white' }}></div>
              <Text size="xs">Portfolios</Text>
            </Group>
          )}
        </Group>
      </Stack>
    </Card>
  );
}

