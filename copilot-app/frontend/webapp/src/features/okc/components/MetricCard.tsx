import type { ReactNode } from 'react';
import { cn, formatCurrency, formatNumber, formatPercentage, getTrendColor, getTrendIcon } from '@/features/okc/utils';

interface MetricCardProps {
  title: string;
  value: number;
  change?: number;
  currency?: boolean;
  percentage?: boolean;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  description?: string;
}

export function MetricCard({
  title,
  value,
  change,
  currency,
  percentage,
  icon,
  trend,
  description,
}: MetricCardProps) {
  const formattedValue = currency
    ? formatCurrency(value)
    : percentage
    ? formatPercentage(value)
    : formatNumber(value, 0);

  return (
    <div className="bg-surface rounded-xl border border-border p-5 shadow-lg transition-all duration-300 hover:scale-[1.02] hover:shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              {icon}
            </div>
          )}
          <div>
            <p className="text-sm text-muted uppercase tracking-wide">{title}</p>
            <p className="text-2xl font-semibold text-text" style={{ fontVariantNumeric: 'tabular-nums' }}>{formattedValue}</p>
          </div>
        </div>
        {trend && (
          <span className={cn('text-xl font-semibold', getTrendColor(trend))}>
            {getTrendIcon(trend)}
          </span>
        )}
      </div>
      {typeof change === 'number' && (
        <div className="flex items-center gap-2 text-sm">
          <span className={getTrendColor(change)}>
            {getTrendIcon(change)} {formatPercentage(Math.abs(change))}
          </span>
          <span className="text-muted">vs période précédente</span>
        </div>
      )}
      {description && <p className="text-sm text-muted mt-2">{description}</p>}
    </div>
  );
}

export function MetricGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">{children}</div>;
}
