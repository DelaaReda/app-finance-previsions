/**
 * TreemapChart - Treemap pour allocation portfolio
 * Visualisation hiérarchique avec tailles proportionnelles
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo } from 'react';

interface TreemapNode {
  id: string;
  label: string;
  value: number; // Taille proportionnelle
  color?: string;
  children?: TreemapNode[];
  metadata?: Record<string, any>;
}

interface TreemapChartProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Données hiérarchiques */
  data: TreemapNode[];
  /** Taille */
  size?: number;
}

const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

export function TreemapChart({
  title,
  description,
  data,
  size = 600,
}: TreemapChartProps) {
  const layout = useMemo(() => {
    // Algorithme simple de treemap (squarified)
    const totalValue = data.reduce((sum, node) => sum + node.value, 0);
    
    const rectangles: Array<{
      node: TreemapNode;
      x: number;
      y: number;
      width: number;
      height: number;
      color: string;
    }> = [];
    
    // Trier par valeur décroissante
    const sorted = [...data].sort((a, b) => b.value - a.value);
    
    // Layout simple en colonnes
    let currentX = 0;
    let currentY = 0;
    let maxHeightInRow = 0;
    const itemsPerRow = Math.ceil(Math.sqrt(sorted.length));
    const itemWidth = 100 / itemsPerRow;
    
    sorted.forEach((node, index) => {
      const row = Math.floor(index / itemsPerRow);
      const col = index % itemsPerRow;
      
      const normalizedValue = (node.value / totalValue) * 100;
      const height = Math.max(normalizedValue * 2, 5); // Min 5% height
      
      rectangles.push({
        node,
        x: col * itemWidth,
        y: currentY,
        width: itemWidth,
        height,
        color: node.color || DEFAULT_COLORS[index % DEFAULT_COLORS.length],
      });
      
      maxHeightInRow = Math.max(maxHeightInRow, height);
      
      if (col === itemsPerRow - 1) {
        currentY += maxHeightInRow;
        maxHeightInRow = 0;
      }
    });
    
    return rectangles;
  }, [data]);

  const maxValue = Math.max(...data.map(d => d.value));
  const minValue = Math.min(...data.map(d => d.value));

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
        </div>
        
        <div style={{ position: 'relative', width: '100%', height: `${size}px` }}>
          {layout.map((rect, index) => {
            const fontSize = Math.max(10, Math.min(14, rect.height * 0.15));
            const showLabel = rect.height > 8 && rect.width > 15;
            
            return (
              <Tooltip
                key={index}
                label={
                  <div>
                    <Text size="sm" fw={600}>{rect.node.label}</Text>
                    <Text size="xs">Valeur: {rect.node.value.toLocaleString()}</Text>
                    <Text size="xs">Part: {((rect.node.value / maxValue) * 100).toFixed(1)}%</Text>
                    {rect.node.metadata && Object.entries(rect.node.metadata).map(([key, value]) => (
                      <Text key={key} size="xs" c="dimmed">{key}: {String(value)}</Text>
                    ))}
                  </div>
                }
                withArrow
              >
                <div
                  style={{
                    position: 'absolute',
                    left: `${rect.x}%`,
                    top: `${rect.y}%`,
                    width: `${rect.width}%`,
                    height: `${rect.height}%`,
                    backgroundColor: rect.color,
                    border: '2px solid white',
                    borderRadius: '4px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    padding: '4px',
                    boxSizing: 'border-box',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scale(1.05)';
                    e.currentTarget.style.zIndex = '10';
                    e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scale(1)';
                    e.currentTarget.style.zIndex = '1';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                >
                  {showLabel && (
                    <>
                      <Text
                        size={fontSize}
                        fw={700}
                        c="white"
                        ta="center"
                        style={{
                          textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                          lineHeight: 1.2,
                        }}
                      >
                        {rect.node.label}
                      </Text>
                      <Text
                        size={fontSize * 0.7}
                        c="white"
                        ta="center"
                        style={{
                          textShadow: '0 1px 2px rgba(0,0,0,0.5)',
                          opacity: 0.9,
                        }}
                      >
                        {((rect.node.value / maxValue) * 100).toFixed(1)}%
                      </Text>
                    </>
                  )}
                </div>
              </Tooltip>
            );
          })}
        </div>
        
        {/* Stats */}
        <Group gap="lg" mt="md">
          <div>
            <Text size="xs" c="dimmed">Total</Text>
            <Text fw={600}>{data.reduce((sum, d) => sum + d.value, 0).toLocaleString()}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Max</Text>
            <Text fw={600}>{maxValue.toLocaleString()}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Éléments</Text>
            <Text fw={600}>{data.length}</Text>
          </div>
        </Group>
      </Stack>
    </Card>
  );
}

