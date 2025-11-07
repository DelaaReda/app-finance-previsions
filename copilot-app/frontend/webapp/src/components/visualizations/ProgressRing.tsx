/**
 * ProgressRing - Ring de progression avec métriques
 * Visualisation circulaire pour scores, pourcentages, etc.
 */

import { Card, Stack, Group, Text, RingProgress, Badge } from '@mantine/core';
import type { ReactNode } from 'react';

interface ProgressRingProps {
  /** Label */
  label: string;
  /** Valeur (0-100) */
  value: number;
  /** Couleur */
  color?: string;
  /** Sous-titre */
  subtitle?: string;
  /** Badge optionnel */
  badge?: {
    label: string;
    color: string;
  };
  /** Icône optionnelle */
  icon?: ReactNode;
  /** Taille */
  size?: number;
  /** Afficher la valeur au centre */
  showValue?: boolean;
}

export function ProgressRing({
  label,
  value,
  color = 'blue',
  subtitle,
  badge,
  icon,
  size = 150,
  showValue = true,
}: ProgressRingProps) {
  return (
    <Card padding="lg" radius="md" withBorder>
      <Stack gap="md" align="center">
        <Group gap="xs" align="center">
          {icon && <div>{icon}</div>}
          <Text fw={600} size="sm">{label}</Text>
          {badge && (
            <Badge color={badge.color} variant="light" size="sm">
              {badge.label}
            </Badge>
          )}
        </Group>
        
        <RingProgress
          size={size}
          thickness={14}
          roundCaps
          sections={[{ value: Math.min(100, Math.max(0, value)), color }]}
          label={
            showValue ? (
              <Text fw={700} fz="xl" ta="center">
                {Math.round(value)}%
              </Text>
            ) : undefined
          }
        />
        
        {subtitle && (
          <Text size="sm" c="dimmed" ta="center">
            {subtitle}
          </Text>
        )}
      </Stack>
    </Card>
  );
}

