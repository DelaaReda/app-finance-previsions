/**
 * SankeyDiagram - Diagramme Sankey pour flux
 * Parfait pour flux de capitaux, allocation, transitions
 */

import { Card, Stack, Title, Text, Group, Tooltip, Badge } from '@mantine/core';
import { useMemo } from 'react';

interface SankeyLink {
  source: string;
  target: string;
  value: number;
  color?: string;
}

interface SankeyNode {
  id: string;
  label: string;
  value?: number; // Valeur totale (calculée si non fourni)
  color?: string;
  category?: string;
}

interface SankeyDiagramProps {
  /** Titre */
  title: string;
  /** Description */
  description?: string;
  /** Nodes */
  nodes: SankeyNode[];
  /** Links */
  links: SankeyLink[];
  /** Hauteur */
  height?: number;
}

export function SankeyDiagram({
  title,
  description,
  nodes,
  links,
  height = 400,
}: SankeyDiagramProps) {
  const layout = useMemo(() => {
    // Organiser nodes en colonnes (sources à gauche, targets à droite)
    const sourceNodes = new Set(links.map(l => l.source));
    const targetNodes = new Set(links.map(l => l.target));
    const middleNodes = nodes.filter(n => !sourceNodes.has(n.id) && !targetNodes.has(n.id));
    
    const leftNodes = nodes.filter(n => sourceNodes.has(n.id));
    const rightNodes = nodes.filter(n => targetNodes.has(n.id));
    
    // Calculer valeurs totales
    const nodeValues = new Map<string, number>();
    links.forEach(link => {
      nodeValues.set(link.source, (nodeValues.get(link.source) || 0) + link.value);
      nodeValues.set(link.target, (nodeValues.get(link.target) || 0) + link.value);
    });
    
    const nodeHeight = height / Math.max(leftNodes.length, rightNodes.length, 1);
    const nodeWidth = 120;
    const gap = 20;
    
    const positionedNodes = new Map<string, {
      x: number;
      y: number;
      width: number;
      height: number;
      node: SankeyNode;
      value: number;
    }>();
    
    // Positionner nodes de gauche
    leftNodes.forEach((node, index) => {
      positionedNodes.set(node.id, {
        x: 0,
        y: index * (nodeHeight + gap),
        width: nodeWidth,
        height: nodeHeight,
        node,
        value: nodeValues.get(node.id) || node.value || 0,
      });
    });
    
    // Positionner nodes de droite
    rightNodes.forEach((node, index) => {
      positionedNodes.set(node.id, {
        x: 600 - nodeWidth,
        y: index * (nodeHeight + gap),
        width: nodeWidth,
        height: nodeHeight,
        node,
        value: nodeValues.get(node.id) || node.value || 0,
      });
    });
    
    return { positionedNodes, links };
  }, [nodes, links, height]);

  const { positionedNodes } = layout;

  const getLinkPath = (
    sourceX: number, sourceY: number, sourceHeight: number,
    targetX: number, targetY: number, targetHeight: number
  ) => {
    const midX = (sourceX + targetX) / 2;
    return `M ${sourceX} ${sourceY + sourceHeight / 2}
            L ${midX} ${sourceY + sourceHeight / 2}
            L ${midX} ${targetY + targetHeight / 2}
            L ${targetX} ${targetY + targetHeight / 2}`;
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
        
        <div style={{ position: 'relative', width: '100%', height: `${height}px`, overflow: 'visible' }}>
          <svg width="600" height={height} style={{ overflow: 'visible' }}>
            {/* Links */}
            {links.map((link, index) => {
              const source = positionedNodes.get(link.source);
              const target = positionedNodes.get(link.target);
              
              if (!source || !target) return null;
              
              const maxValue = Math.max(...links.map(l => l.value));
              const linkWidth = Math.max(2, (link.value / maxValue) * 20);
              const color = link.color || '#3b82f6';
              
              const path = getLinkPath(
                source.x + source.width,
                source.y,
                source.height,
                target.x,
                target.y,
                target.height
              );
              
              return (
                <Tooltip
                  key={index}
                  label={
                    <div>
                      <Text size="sm" fw={600}>{source.node.label} → {target.node.label}</Text>
                      <Text size="xs">Valeur: {link.value.toLocaleString()}</Text>
                    </div>
                  }
                  withArrow
                >
                  <path
                    d={path}
                    stroke={color}
                    strokeWidth={linkWidth}
                    fill="none"
                    opacity={0.6}
                    style={{ cursor: 'pointer' }}
                  />
                </Tooltip>
              );
            })}
            
            {/* Nodes */}
            {Array.from(positionedNodes.values()).map((pos, index) => {
              const color = pos.node.color || '#3b82f6';
              
              return (
                <Tooltip
                  key={index}
                  label={
                    <div>
                      <Text size="sm" fw={600}>{pos.node.label}</Text>
                      <Text size="xs">Valeur: {pos.value.toLocaleString()}</Text>
                      {pos.node.category && (
                        <Text size="xs" c="dimmed">Catégorie: {pos.node.category}</Text>
                      )}
                    </div>
                  }
                  withArrow
                >
                  <g
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.opacity = '0.8';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.opacity = '1';
                    }}
                  >
                    <rect
                      x={pos.x}
                      y={pos.y}
                      width={pos.width}
                      height={pos.height}
                      fill={color}
                      rx="4"
                      stroke="white"
                      strokeWidth={2}
                    />
                    <text
                      x={pos.x + pos.width / 2}
                      y={pos.y + pos.height / 2 - 8}
                      textAnchor="middle"
                      fontSize="11"
                      fontWeight="600"
                      fill="white"
                      style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
                    >
                      {pos.node.label}
                    </text>
                    <text
                      x={pos.x + pos.width / 2}
                      y={pos.y + pos.height / 2 + 8}
                      textAnchor="middle"
                      fontSize="10"
                      fill="white"
                      style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
                    >
                      {pos.value.toLocaleString()}
                    </text>
                  </g>
                </Tooltip>
              );
            })}
          </svg>
        </div>
        
        {/* Stats */}
        <Group gap="lg" mt="md">
          <div>
            <Text size="xs" c="dimmed">Total Flux</Text>
            <Text fw={600}>{links.reduce((sum, l) => sum + l.value, 0).toLocaleString()}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Nodes</Text>
            <Text fw={600}>{nodes.length}</Text>
          </div>
          <div>
            <Text size="xs" c="dimmed">Links</Text>
            <Text fw={600}>{links.length}</Text>
          </div>
        </Group>
      </Stack>
    </Card>
  );
}

