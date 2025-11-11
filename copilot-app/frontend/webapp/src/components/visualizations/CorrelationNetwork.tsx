/**
 * CorrelationNetwork - Graph network de corrélations
 * Visualisation interactive des relations entre tickers
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo, useState } from 'react';

interface CorrelationLink {
  source: string;
  target: string;
  correlation: number; // -1 à 1
  strength?: 'strong' | 'moderate' | 'weak';
}

interface CorrelationNetworkProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Liens de corrélation */
  links: CorrelationLink[];
  /** Tickers (nodes) */
  nodes: Array<{
    id: string;
    label?: string;
    sector?: string;
    size?: number;
  }>;
  /** Seuil de corrélation minimum */
  threshold?: number;
  /** Taille */
  size?: number;
}

export function CorrelationNetwork({
  title,
  description,
  links,
  nodes,
  threshold = 0.5,
  size = 600,
}: CorrelationNetworkProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  
  const filteredLinks = useMemo(() => {
    return links.filter(l => Math.abs(l.correlation) >= threshold);
  }, [links, threshold]);

  const nodeMap = useMemo(() => {
    const map = new Map();
    nodes.forEach(node => {
      map.set(node.id, node);
    });
    return map;
  }, [nodes]);

  // Position des nodes en cercle
  const nodePositions = useMemo(() => {
    const positions = new Map();
    const radius = size * 0.35;
    const centerX = size / 2;
    const centerY = size / 2;
    
    nodes.forEach((node, index) => {
      const angle = (index / nodes.length) * 2 * Math.PI - Math.PI / 2;
      positions.set(node.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });
    
    return positions;
  }, [nodes, size]);

  const getLinkColor = (correlation: number) => {
    if (correlation > 0.7) return '#10b981'; // Teal - forte positive
    if (correlation > 0.3) return '#3b82f6'; // Blue - modérée positive
    if (correlation > -0.3) return '#6b7280'; // Gray - faible
    if (correlation > -0.7) return '#f59e0b'; // Orange - modérée négative
    return '#ef4444'; // Red - forte négative
  };

  const getLinkWidth = (correlation: number) => {
    return Math.abs(correlation) * 3 + 1;
  };

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md">
        <div>
          <Title order={4} mb={4}>{title}</Title>
          {description && (
            <Text size="sm" c="dimmed">{description}</Text>
          )}
          <Badge variant="light" mt={4}>
            {filteredLinks.length} liens (seuil: {threshold})
          </Badge>
        </div>
        
        <div style={{ position: 'relative', width: '100%', height: `${size}px`, overflow: 'visible' }}>
          <svg width={size} height={size} style={{ overflow: 'visible' }}>
            {/* Links */}
            {filteredLinks.map((link, index) => {
              const sourcePos = nodePositions.get(link.source);
              const targetPos = nodePositions.get(link.target);
              
              if (!sourcePos || !targetPos) return null;
              
              const color = getLinkColor(link.correlation);
              const width = getLinkWidth(link.correlation);
              const opacity = Math.abs(link.correlation) * 0.6 + 0.2;
              
              return (
                <Tooltip
                  key={index}
                  label={
                    <div>
                      <Text size="sm" fw={600}>{link.source} ↔ {link.target}</Text>
                      <Text size="xs">Corrélation: {(link.correlation * 100).toFixed(1)}%</Text>
                    </div>
                  }
                  withArrow
                >
                  <line
                    x1={sourcePos.x}
                    y1={sourcePos.y}
                    x2={targetPos.x}
                    y2={targetPos.y}
                    stroke={color}
                    strokeWidth={width}
                    opacity={opacity}
                    style={{ cursor: 'pointer' }}
                  />
                </Tooltip>
              );
            })}
            
            {/* Nodes */}
            {nodes.map((node) => {
              const pos = nodePositions.get(node.id);
              if (!pos) return null;
              
              const isSelected = selectedNode === node.id;
              const nodeSize = node.size || 20;
              
              return (
                <Tooltip
                  key={node.id}
                  label={
                    <div>
                      <Text size="sm" fw={600}>{node.label || node.id}</Text>
                      {node.sector && (
                        <Text size="xs" c="dimmed">Secteur: {node.sector}</Text>
                      )}
                    </div>
                  }
                  withArrow
                >
                  <g
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedNode(isSelected ? null : node.id)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'scale(1.2)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'scale(1)';
                    }}
                  >
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={isSelected ? nodeSize + 5 : nodeSize}
                      fill={isSelected ? '#3b82f6' : '#10b981'}
                      stroke="white"
                      strokeWidth={isSelected ? 3 : 2}
                      style={{ transition: 'all 0.2s' }}
                    />
                    <text
                      x={pos.x}
                      y={pos.y + nodeSize + 15}
                      textAnchor="middle"
                      fontSize="11"
                      fontWeight="600"
                      fill="white"
                      style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
                    >
                      {node.id}
                    </text>
                  </g>
                </Tooltip>
              );
            })}
          </svg>
        </div>
        
        {/* Legend */}
        <Group gap="lg" mt="md" wrap="wrap">
          <Group gap="xs">
            <div style={{ width: 20, height: 3, backgroundColor: '#10b981' }}></div>
            <Text size="xs">Forte corrélation positive</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 2, backgroundColor: '#6b7280' }}></div>
            <Text size="xs">Faible corrélation</Text>
          </Group>
          <Group gap="xs">
            <div style={{ width: 20, height: 3, backgroundColor: '#ef4444' }}></div>
            <Text size="xs">Forte corrélation négative</Text>
          </Group>
        </Group>
      </Stack>
    </Card>
  );
}

