/**
 * PerformanceGauge - Gauge chart pour métriques de performance
 * Style Bloomberg Terminal / TradingView
 */

import { Card, Stack, Text, Group, Badge } from '@mantine/core';
import { RingProgress } from '@mantine/core';
import type { ReactNode } from 'react';

interface PerformanceGaugeProps {
  /** Label */
  label: string;
  /** Valeur actuelle */
  value: number;
  /** Valeur minimale */
  min?: number;
  /** Valeur maximale */
  max?: number;
  /** Seuils de couleur */
  thresholds?: Array<{
    value: number;
    color: string;
    label: string;
  }>;
  /** Icône */
  icon?: ReactNode;
  /** Sous-titre */
  subtitle?: string;
  /** Taille */
  size?: number;
}

export function PerformanceGauge({
  label,
  value,
  min = 0,
  max = 100,
  thresholds = [
    { value: 0, color: 'red', label: 'Faible' },
    { value: 50, color: 'orange', label: 'Moyen' },
    { value: 75, color: 'teal', label: 'Élevé' },
  ],
  icon,
  subtitle,
  size = 200,
}: PerformanceGaugeProps) {
  const normalizedValue = ((value - min) / (max - min)) * 100;
  const clampedValue = Math.min(100, Math.max(0, normalizedValue));
  
  // Trouver la couleur selon les seuils
  const getColor = () => {
    for (let i = thresholds.length - 1; i >= 0; i--) {
      const threshold = thresholds[i];
      const thresholdPercent = ((threshold.value - min) / (max - min)) * 100;
      if (clampedValue >= thresholdPercent) {
        return threshold.color;
      }
    }
    return thresholds[0]?.color || 'gray';
  };

  const color = getColor();
  
  // Créer les sections pour le gauge
  const sections = thresholds.map((threshold, index) => {
    const thresholdPercent = ((threshold.value - min) / (max - min)) * 100;
    const nextThreshold = thresholds[index + 1];
    const nextPercent = nextThreshold 
      ? ((nextThreshold.value - min) / (max - min)) * 100 
      : 100;
    const width = nextPercent - thresholdPercent;
    
    return {
      value: width,
      color: threshold.color,
    };
  });

  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md" align="center">
        <Group gap="xs" align="center">
          {icon && <div>{icon}</div>}
          <Text fw={600} size="sm">{label}</Text>
        </Group>
        
        <div style={{ position: 'relative' }}>
          <RingProgress
            size={size}
            thickness={20}
            roundCaps
            sections={sections}
            label={
              <div style={{ textAlign: 'center' }}>
                <Text fw={700} fz="xl" c={color}>
                  {value.toFixed(1)}
                </Text>
                <Text size="xs" c="dimmed">
                  / {max}
                </Text>
              </div>
            }
          />
          {/* Indicateur de valeur actuelle */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '4px',
              height: `${size * 0.3}px`,
              backgroundColor: color,
              borderRadius: '2px',
              transformOrigin: 'bottom center',
              transform: `translate(-50%, -50%) rotate(${(clampedValue / 100) * 360 - 90}deg)`,
              zIndex: 10,
            }}
          />
        </div>
        
        {subtitle && (
          <Text size="sm" c="dimmed" ta="center">
            {subtitle}
          </Text>
        )}
        
        {/* Badge de seuil */}
        <Badge
          color={color}
          variant="light"
          size="lg"
        >
          {thresholds.find(t => {
            const tPercent = ((t.value - min) / (max - min)) * 100;
            return clampedValue >= tPercent;
          })?.label || thresholds[0]?.label}
        </Badge>
      </Stack>
    </Card>
  );
}

