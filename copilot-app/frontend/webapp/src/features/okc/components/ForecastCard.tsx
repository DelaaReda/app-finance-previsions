import { useState } from 'react';
import { IconArrowUpRight, IconArrowDownRight, IconArrowRight, IconTarget, IconClock, IconAlertTriangle } from '@tabler/icons-react';
import { cn, formatPercentage } from '@/features/okc/utils';

export interface ForecastInsight {
  id: string;
  ticker: string;
  horizon?: string;
  direction?: 'up' | 'down' | 'neutral';
  confidence?: number;
  expectedReturn?: number;
  reason?: string;
  riskFactors?: string[];
  lastUpdated?: string;
}

const directionCopy: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  up: { label: 'Haussier', color: 'text-success', icon: <IconArrowUpRight size={16} /> },
  down: { label: 'Baissier', color: 'text-danger', icon: <IconArrowDownRight size={16} /> },
  neutral: { label: 'Neutre', color: 'text-muted', icon: <IconArrowRight size={16} /> },
};

export function ForecastCard({ forecast }: { forecast: ForecastInsight }) {
  const [expanded, setExpanded] = useState(false);
  const direction = forecast.direction ?? 'neutral';
  const directionInfo = directionCopy[direction] ?? directionCopy.neutral;
  const expectedPct = typeof forecast.expectedReturn === 'number' ? forecast.expectedReturn * 100 : undefined;
  const confidencePct = typeof forecast.confidence === 'number' ? Math.round(forecast.confidence * 100) : undefined;

  return (
    <div className="bg-surface rounded-xl border border-border p-5 shadow-lg transition-all duration-300 hover:scale-[1.01] hover:shadow-xl">
      <button className="w-full text-left hover:bg-surface-elevated/30 rounded-lg p-2 -m-2 transition-colors" onClick={() => setExpanded((prev) => !prev)}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted">Prévision</p>
            <h4 className="text-2xl font-semibold text-text">{forecast.ticker}</h4>
            <p className="text-sm text-muted">{forecast.horizon ?? 'Horizon mixte'}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-muted">Direction</p>
            <span className={cn('flex items-center gap-1 justify-end font-semibold', directionInfo.color)}>
              {directionInfo.icon}
              {directionInfo.label}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mt-5">
          <div className="rounded-lg bg-surface-elevated/60 border border-border p-3">
            <p className="text-xs text-muted mb-1">Confiance</p>
            <p className="text-xl font-semibold text-text flex items-center gap-2">
              <IconTarget size={16} />
              {confidencePct !== undefined ? `${confidencePct}%` : 'N/A'}
            </p>
          </div>
          <div className="rounded-lg bg-surface-elevated/60 border border-border p-3">
            <p className="text-xs text-muted mb-1">Rendement attendu</p>
            <p className="text-xl font-semibold text-text flex items-center gap-2">
              {expectedPct !== undefined ? formatPercentage(expectedPct, 2) : 'N/A'}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between mt-4 text-xs text-muted">
          <span className="flex items-center gap-1">
            <IconClock size={14} />
            {forecast.lastUpdated ? new Date(forecast.lastUpdated).toLocaleString('fr-FR') : 'MAJ inconnue'}
          </span>
          <span className="flex items-center gap-2 text-primary text-sm">
            {expanded ? 'Réduire' : 'Voir les détails'}
            <IconArrowRight size={14} className={cn('transition-transform', expanded && 'rotate-90')} />
          </span>
        </div>
      </button>

      {expanded && (
        <div className="mt-4 border-t border-border pt-4 space-y-4 text-sm animate-slide-down">
          {forecast.reason && (
            <div>
              <p className="text-muted mb-2">Analyse</p>
              <p className="text-text/90 leading-relaxed">{forecast.reason}</p>
            </div>
          )}
          {forecast.riskFactors && forecast.riskFactors.length > 0 && (
            <div>
              <p className="text-muted mb-2 flex items-center gap-2">
                <IconAlertTriangle size={14} />
                Risques surveillés
              </p>
              <ul className="list-disc pl-5 space-y-1 text-text/80">
                {forecast.riskFactors.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
