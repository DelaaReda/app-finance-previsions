/**
 * KPI Bar - Barre compacte en haut du dashboard
 * Affiche les KPIs essentiels + fraîcheur des données
 */

import { useMemo } from 'react';
import { IconRefresh, IconTrendingUp, IconTarget, IconClock } from '@tabler/icons-react';
import { useDashboardKPIs } from '@/hooks/useDashboardKPIs';
import { useForecasts } from '@/hooks/useForecasts';
import { Button } from '@/features/okc/components/Button';

interface KPIBarProps {
  onRefresh?: () => void;
}

export function KPIBar({ onRefresh }: KPIBarProps) {
  const kpisQuery = useDashboardKPIs();
  const forecastsQuery = useForecasts();

  const kpis = useMemo(() => {
    const data = kpisQuery.data;
    const forecasts = forecastsQuery.data;
    
    // Calculer les métriques à partir des données réelles
    const forecastRows = forecasts?.rows || [];
    const totalForecasts = forecastRows.length;
    const highConfidenceCount = forecastRows.filter(row => (row.confidence || 0) >= 0.7).length;
    const avgConfidence = totalForecasts > 0 
      ? forecastRows.reduce((sum, row) => sum + (row.confidence || 0), 0) / totalForecasts 
      : 0;

    // Calculer le taux de réussite (simulation basée sur les données KPI)
    const hitRate = data?.backtests?.hit_rate || 0;

    return {
      activeForecasts: totalForecasts,
      avgConfidence: Math.round(avgConfidence * 100),
      hitRate: Math.round(hitRate * 100),
      lastUpdate: forecasts?.freshness || data?.system?.last_forecast_update || data?.generated_at
    };
  }, [kpisQuery.data, forecastsQuery.data]);

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'Inconnue';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffMinutes < 1) return 'À l\'instant';
    if (diffMinutes < 60) return `${diffMinutes} min`;
    if (diffMinutes < 24 * 60) return `${Math.floor(diffMinutes / 60)}h`;
    return `${Math.floor(diffMinutes / (24 * 60))}j`;
  };

  const isLoading = kpisQuery.isLoading || forecastsQuery.isLoading;

  return (
    <div className="bg-zinc-900/70 border border-zinc-800 rounded-xl p-4 mb-6">
      <div className="flex items-center justify-between gap-6">
        {/* KPIs principaux */}
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2">
            <IconTrendingUp size={16} className="text-emerald-400 opacity-70" />
            <div>
              <span className="text-xs uppercase tracking-wide text-gray-400">Prévisions actives</span>
              <div className="text-lg font-semibold text-gray-100">
                {isLoading ? '—' : kpis.activeForecasts}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <IconTarget size={16} className="text-blue-400 opacity-70" />
            <div>
              <span className="text-xs uppercase tracking-wide text-gray-400">Confiance moyenne</span>
              <div className="text-lg font-semibold text-gray-100">
                {isLoading ? '—' : `${kpis.avgConfidence}%`}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <IconTarget size={16} className="text-green-400 opacity-70" />
            <div>
              <span className="text-xs uppercase tracking-wide text-gray-400">Taux de réussite</span>
              <div className="text-lg font-semibold text-gray-100">
                {isLoading ? '—' : `${kpis.hitRate}%`}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <IconClock size={16} className="text-orange-400 opacity-70" />
            <div>
              <span className="text-xs uppercase tracking-wide text-gray-400">Dernière MAJ</span>
              <div className="text-lg font-semibold text-gray-100">
                {isLoading ? '—' : formatTimestamp(kpis.lastUpdate)}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            className="h-8 px-3 text-sm"
            onClick={onRefresh}
            disabled={isLoading}
          >
            <IconRefresh size={16} className={isLoading ? 'animate-spin' : ''} />
            Rafraîchir
          </Button>
        </div>
      </div>
    </div>
  );
}