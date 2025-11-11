/**
 * OKMetricCard Component - From OKComputer Design
 * Metric card component for displaying financial metrics with trends
 */
import React from 'react';
import { cn, formatCurrency, formatPercentage, getTrendColor, getTrendIcon } from '@/lib/utils';

export interface OKMetricCardProps {
  title: string;
  value: number;
  change?: number;
  currency?: boolean;
  percentage?: boolean;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
  description?: string;
}

export const OKMetricCard: React.FC<OKMetricCardProps> = ({
  title,
  value,
  change,
  currency = false,
  percentage = false,
  icon,
  trend,
  className,
  description,
}) => {
  const formattedValue = currency 
    ? formatCurrency(value)
    : percentage 
    ? formatPercentage(value)
    : value.toLocaleString();

  const trendIcon = trend ? getTrendIcon(trend === 'up' ? 1 : trend === 'down' ? -1 : 0) : '';
  const trendColor = trend ? getTrendColor(trend === 'up' ? 1 : trend === 'down' ? -1 : 0) : '';

  return (
    <div className={cn(
      'bg-surface rounded-xl border border-border p-6 shadow-lg transition-all duration-300 hover:scale-105 hover:shadow-xl',
      className
    )}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
              {icon}
            </div>
          )}
          <div>
            <h3 className="text-sm font-medium text-muted">{title}</h3>
            <p className="text-2xl font-bold text-text">{formattedValue}</p>
          </div>
        </div>
        {trend && (
          <span className={cn('text-lg font-semibold', trendColor)}>
            {trendIcon}
          </span>
        )}
      </div>
      
      {change !== undefined && (
        <div className="flex items-center gap-2">
          <span className={cn('text-sm font-medium', getTrendColor(change))}>
            {getTrendIcon(change)} {formatPercentage(Math.abs(change))}
          </span>
          <span className="text-sm text-muted">vs last period</span>
        </div>
      )}
      
      {description && (
        <p className="text-sm text-muted mt-2">{description}</p>
      )}
    </div>
  );
};

export const OKMetricGrid: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className,
}) => {
  return (
    <div className={cn('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6', className)}>
      {children}
    </div>
  );
};

export default OKMetricCard;

