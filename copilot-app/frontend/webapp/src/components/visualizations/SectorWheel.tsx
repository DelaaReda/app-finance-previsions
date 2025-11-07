/**
 * SectorWheel - Roue de secteurs avec allocation
 * Visualisation circulaire pour répartition portfolio
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo } from 'react';

interface SectorData {
  sector: string;
  weight: number; // 0-100
  color?: string;
  tickers?: string[];
}

interface SectorWheelProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données secteurs */
  data: SectorData[];
  /** Taille */
  size?: number;
}

const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

export function SectorWheel({
  title,
  description,
  data,
  size = 300,
}: SectorWheelProps) {
  const processedData = useMemo(() => {
    const sorted = [...data].sort((a, b) => b.weight - a.weight);
    let currentAngle = -90; // Start at top
    
    return sorted.map((sector, index) => {
      const angle = (sector.weight / 100) * 360;
      const startAngle = currentAngle;
      const endAngle = currentAngle + angle;
      currentAngle = endAngle;
      
      return {
        ...sector,
        color: sector.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
        startAngle,
        endAngle,
        angle,
        midAngle: (startAngle + endAngle) / 2,
      };
    });
  }, [data]);

  const totalWeight = data.reduce((sum, d) => sum + d.weight, 0);
  const radius = size / 2;
  const innerRadius = radius * 0.4;

  const getPath = (startAngle: number, endAngle: number, outerRadius: number, innerRadius: number) => {
    const start = polarToCartesian(radius, radius, outerRadius, startAngle);
    const end = polarToCartesian(radius, radius, outerRadius, endAngle);
    const innerStart = polarToCartesian(radius, radius, innerRadius, startAngle);
    const innerEnd = polarToCartesian(radius, radius, innerRadius, endAngle);
    
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    
    return [
      `M ${start.x} ${start.y}`,
      `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${end.x} ${end.y}`,
      `L ${innerEnd.x} ${innerEnd.y}`,
      `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
      'Z',
    ].join(' ');
  };

  const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians)),
    };
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
        
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <svg width={size} height={size} style={{ transform: 'rotate(0deg)' }}>
            {processedData.map((sector, index) => (
              <Tooltip
                key={index}
                label={
                  <div>
                    <Text size="sm" fw={600}>{sector.sector}</Text>
                    <Text size="xs">{sector.weight.toFixed(1)}%</Text>
                    {sector.tickers && sector.tickers.length > 0 && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {sector.tickers.slice(0, 5).join(', ')}
                        {sector.tickers.length > 5 && ` +${sector.tickers.length - 5}`}
                      </Text>
                    )}
                  </div>
                }
                withArrow
              >
                <path
                  d={getPath(sector.startAngle, sector.endAngle, radius, innerRadius)}
                  fill={sector.color}
                  stroke="white"
                  strokeWidth={2}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.opacity = '0.8';
                    e.currentTarget.style.transform = 'scale(1.05)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.opacity = '1';
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                />
              </Tooltip>
            ))}
            
            {/* Center circle */}
            <circle
              cx={radius}
              cy={radius}
              r={innerRadius}
              fill="var(--mantine-color-dark-7)"
              stroke="var(--mantine-color-dark-5)"
              strokeWidth={2}
            />
            <text
              x={radius}
              y={radius - 10}
              textAnchor="middle"
              fill="white"
              fontSize="20"
              fontWeight="700"
            >
              {totalWeight.toFixed(0)}%
            </text>
            <text
              x={radius}
              y={radius + 10}
              textAnchor="middle"
              fill="var(--mantine-color-gray-5)"
              fontSize="12"
            >
              Total
            </text>
          </svg>
        </div>
        
        {/* Legend */}
        <Group gap="md" mt="md" wrap="wrap">
          {processedData.slice(0, 8).map((sector, index) => (
            <Group key={index} gap="xs">
              <div style={{
                width: 16,
                height: 16,
                backgroundColor: sector.color,
                borderRadius: '4px',
              }} />
              <Text size="xs">
                {sector.sector} ({sector.weight.toFixed(1)}%)
              </Text>
            </Group>
          ))}
        </Group>
      </Stack>
    </Card>
  );
}

