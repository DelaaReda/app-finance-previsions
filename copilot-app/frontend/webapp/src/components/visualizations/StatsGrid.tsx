/**
 * StatsGrid - Grille de métriques visuelles
 * Template réutilisable pour afficher plusieurs métriques avec graphiques
 */

import { SimpleGrid } from '@mantine/core';
import { MetricCard } from './MetricCard';
import type { MetricCardProps } from './MetricCard';

interface StatsGridProps {
  /** Métriques à afficher */
  metrics: Array<MetricCardProps>;
  /** Nombre de colonnes */
  cols?: { base?: number; sm?: number; md?: number; lg?: number };
}

export function StatsGrid({ metrics, cols = { base: 1, sm: 2, md: 2, lg: 4 } }: StatsGridProps) {
  return (
    <SimpleGrid cols={cols} spacing="lg">
      {metrics.map((metric, index) => (
        <MetricCard key={index} {...metric} />
      ))}
    </SimpleGrid>
  );
}

