/**
 * Macro Snapshot - Composant compact pour indicateurs macroéconomiques
 * P0 Fix: Évite la duplication de libellés, formatage cohérent
 */

import { useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/features/okc/components/Card';
import { Badge } from '@mantine/core';
import { IconAlertCircle, IconTrendingUp, IconTrendingDown } from '@tabler/icons-react';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatNumber } from '@/lib/formatting';

interface MacroIndicator {
  id: string;
  label: string;
  value: number;
  unit?: string;
}

interface MacroSnapshotProps {
  data: any;
  isLoading: boolean;
  error: any;
  onRefresh?: () => void;
}

const INDICATOR_CONFIG = {
  CPIAUCSL: { label: 'IPC', unit: '', thresholds: { low: 2, high: 4 } },
  UNRATE: { label: 'Chômage', unit: '%', thresholds: { low: 4, high: 6 } },
  DGS10: { label: 'T-Bond 10Y', unit: '%', thresholds: { low: 3, high: 5 } },
  DGS2: { label: 'T-Bond 2Y', unit: '%', thresholds: { low: 2, high: 4 } },
  VIXCLS: { label: 'VIX', unit: '', thresholds: { low: 15, high: 25 } },
} as const;

function getIndicatorStatus(id: string, value: number): { level: 'low' | 'moderate' | 'high'; color: string } {
  const config = INDICATOR_CONFIG[id as keyof typeof INDICATOR_CONFIG];
  if (!config) return { level: 'moderate', color: 'gray' };

  if (value < config.thresholds.low) return { level: 'low', color: 'green' };
  if (value < config.thresholds.high) return { level: 'moderate', color: 'yellow' };
  return { level: 'high', color: 'red' };
}

export function MacroSnapshot({ data, isLoading, error, onRefresh }: MacroSnapshotProps) {
  const indicators = useMemo(() => {
    if (!data || typeof data !== 'object') return [];

    // Extraire les données selon différents formats possibles
    const series = Array.isArray(data.series) ? data.series : 
                   Array.isArray(data.data?.series) ? data.data.series : [];
    
    const indicators: MacroIndicator[] = [];
    
    series.forEach((s: any) => {
      const id = s.id ?? s.series_id ?? s.name;
      if (!id || !(id in INDICATOR_CONFIG)) return;

      // Obtenir la dernière valeur
      const points = Array.isArray(s.points) ? s.points : Array.isArray(s.data) ? s.data : [];
      if (points.length === 0) return;

      const lastPoint = points[points.length - 1];
      const value = typeof lastPoint?.value === 'number' ? lastPoint.value : 
                    Array.isArray(lastPoint) ? lastPoint[1] : null;

      if (typeof value === 'number') {
        indicators.push({
          id,
          label: INDICATOR_CONFIG[id as keyof typeof INDICATOR_CONFIG].label,
          value,
          unit: INDICATOR_CONFIG[id as keyof typeof INDICATOR_CONFIG].unit
        });
      }
    });

    return indicators;
  }, [data]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Indicateurs Macro</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="py-8 text-center text-sm text-gray-400">
            Chargement des indicateurs...
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Indicateurs Macro</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Erreur de chargement"
            description="Impossible de charger les indicateurs macroéconomiques"
            icon={<IconAlertCircle size={32} className="text-red-400" />}
            action={{ label: 'Réessayer', onClick: onRefresh }}
          />
        </CardContent>
      </Card>
    );
  }

  if (indicators.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Indicateurs Macro</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            title="Aucun indicateur"
            description="Les données macroéconomiques seront disponibles sous peu"
            action={{ label: 'Rafraîchir', onClick: onRefresh }}
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Indicateurs Macro</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {indicators.map((indicator) => {
            const status = getIndicatorStatus(indicator.id, indicator.value);
            
            return (
              <div 
                key={indicator.id}
                className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-3"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs uppercase tracking-wide text-gray-400">
                    {indicator.label}
                  </span>
                  <Badge
                    size="xs"
                    variant="light"
                    color={status.color}
                  >
                    {status.level}
                  </Badge>
                </div>
                
                <div className="flex items-center gap-2">
                  <span className="text-lg font-semibold text-gray-100">
                    {formatNumber(indicator.value)}
                    {indicator.unit && <span className="text-sm text-gray-400 ml-1">{indicator.unit}</span>}
                  </span>
                  
                  {/* Icône de tendance basée sur la valeur */}
                  {indicator.id === 'VIXCLS' && (
                    indicator.value > 20 ? 
                    <IconTrendingUp size={14} className="text-red-400" /> : 
                    <IconTrendingDown size={14} className="text-green-400" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}