/**
 * OKForecastCard Component - From OKComputer Design
 * Adapted to use real API data from Finance Copilot
 */
import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Calendar, 
  Target, 
  AlertCircle,
  CheckCircle,
  Clock,
  DollarSign,
  Percent,
  ArrowUpRight,
  ArrowDownRight,
  ArrowRight
} from 'lucide-react';
import { cn, formatCurrency, formatPercentage, getTrendColor } from '@/lib/utils';

export interface OKForecast {
  id?: string;
  ticker: string;
  symbol?: string;
  horizon?: string;
  timeframe?: string;
  currentValue?: number;
  predictedValue?: number;
  expected_return?: number;
  expected_return_pct?: number;
  expectedReturnPct?: number;
  confidence: number;
  direction: 'up' | 'down' | 'neutral' | 'flat' | 'bullish' | 'bearish';
  trend?: 'bullish' | 'bearish' | 'neutral';
  rationale?: string;
  explanation?: string;
  factors?: string[];
  risk_factors?: string[];
  lastUpdated?: string;
  timestamp?: string;
  forecasted_at?: string;
  updatedAt?: string;
}

export interface OKForecastCardProps {
  forecast: OKForecast;
  className?: string;
  expanded?: boolean;
  onToggle?: () => void;
  onSelectTicker?: (ticker: string) => void;
}

const trendIcons = {
  bullish: <TrendingUp className="w-4 h-4" />,
  bearish: <TrendingDown className="w-4 h-4" />,
  neutral: <Minus className="w-4 h-4" />,
  up: <TrendingUp className="w-4 h-4" />,
  down: <TrendingDown className="w-4 h-4" />,
  flat: <Minus className="w-4 h-4" />,
};

const trendColors = {
  bullish: 'text-success',
  bearish: 'text-danger',
  neutral: 'text-muted',
  up: 'text-success',
  down: 'text-danger',
  flat: 'text-muted',
};

const trendBgColors = {
  bullish: 'bg-success/10',
  bearish: 'bg-danger/10',
  neutral: 'bg-muted/10',
  up: 'bg-success/10',
  down: 'bg-danger/10',
  flat: 'bg-muted/10',
};

// Normalize direction to trend
function normalizeTrend(direction?: string): 'bullish' | 'bearish' | 'neutral' {
  if (!direction) return 'neutral';
  const d = direction.toLowerCase();
  if (d === 'up' || d === 'bullish' || d === 'buy') return 'bullish';
  if (d === 'down' || d === 'bearish' || d === 'sell') return 'bearish';
  return 'neutral';
}

export const OKForecastCard: React.FC<OKForecastCardProps> = ({
  forecast,
  className,
  expanded = false,
  onToggle,
  onSelectTicker,
}) => {
  const trend = normalizeTrend(forecast.direction || forecast.trend);
  
  // Calculate predicted change from expected return
  const expectedReturn = forecast.expected_return_pct ?? forecast.expectedReturnPct ?? (forecast.expected_return ? forecast.expected_return * 100 : 0);
  const currentValue = forecast.currentValue ?? 100; // Default to 100 if not provided
  const predictedValue = forecast.predictedValue ?? (currentValue * (1 + expectedReturn / 100));
  const predictedChange = expectedReturn;
  const isPositive = predictedChange > 0;

  const formatValue = (value: number) => {
    // For financial forecasts, use percentage format
    return formatPercentage(value);
  };

  const confidenceColor = forecast.confidence >= 80 ? 'text-success' : 
                         forecast.confidence >= 60 ? 'text-warning' : 'text-danger';

  const ticker = forecast.ticker || forecast.symbol || 'N/A';
  const timeframe = forecast.horizon || forecast.timeframe || 'N/A';
  const rationale = forecast.rationale || forecast.explanation || '';
  const factors = forecast.factors || forecast.risk_factors || [];

  return (
    <div
      className={cn(
        'bg-surface rounded-xl border border-border shadow-lg overflow-hidden transition-all duration-300 hover:shadow-xl',
        className
      )}
    >
      {/* Header */}
      <div 
        className="p-6 cursor-pointer hover:bg-surface-elevated transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center',
              trendBgColors[trend]
            )}>
              <div className={trendColors[trend]}>
                {trendIcons[trend]}
              </div>
            </div>
            <div>
              <h3 
                className="text-lg font-semibold text-text cursor-pointer hover:text-primary transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectTicker?.(ticker);
                }}
              >
                {ticker}
              </h3>
              <p className="text-sm text-muted">{timeframe}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className={cn('flex items-center gap-1 text-sm font-medium', confidenceColor)}>
              <Target className="w-4 h-4" />
              {Math.round(forecast.confidence * 100)}% confidence
            </div>
          </div>
        </div>

        {/* Values */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-sm text-muted mb-1">Current</p>
            <p className="text-xl font-bold text-text">{formatValue(currentValue)}</p>
          </div>
          <div>
            <p className="text-sm text-muted mb-1">Predicted</p>
            <p className="text-xl font-bold text-primary">{formatValue(predictedValue)}</p>
          </div>
          <div>
            <p className="text-sm text-muted mb-1">Change</p>
            <div className={cn('flex items-center gap-1', getTrendColor(predictedChange))}>
              {isPositive ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
              <span className="text-xl font-bold">{formatPercentage(Math.abs(predictedChange))}</span>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-muted/20 rounded-full h-2 mb-4">
          <div
            className={cn('h-2 rounded-full transition-all duration-1000 ease-out', 
              forecast.confidence >= 80 ? 'bg-success' :
              forecast.confidence >= 60 ? 'bg-warning' : 'bg-danger'
            )}
            style={{ width: `${forecast.confidence * 100}%` }}
          />
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between text-sm text-muted">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              Last updated: {forecast.lastUpdated || forecast.timestamp || forecast.forecasted_at || forecast.updatedAt 
                ? new Date(forecast.lastUpdated || forecast.timestamp || forecast.forecasted_at || forecast.updatedAt || '').toLocaleDateString()
                : 'N/A'}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <span>Click to expand</span>
            <ArrowRight 
              className={cn('w-4 h-4 transition-transform duration-300', expanded && 'rotate-90')} 
            />
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div
          className="border-t border-border animate-slide-down"
        >
            <div className="p-6 space-y-6">
              {/* Rationale */}
              {rationale && (
                <div>
                  <h4 className="text-sm font-semibold text-text mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-primary" />
                    Analysis Rationale
                  </h4>
                  <p className="text-sm text-muted leading-relaxed">{rationale}</p>
                </div>
              )}

              {/* Key Factors */}
              {factors && factors.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-success" />
                    Key Factors
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {factors.map((factor, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-2 text-sm text-muted animate-fade-in"
                        style={{ animationDelay: `${index * 0.1}s` }}
                      >
                        <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                        {factor}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-3 pt-4 border-t border-border">
                <button 
                  className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelectTicker?.(ticker);
                  }}
                >
                  View Details
                </button>
                <button className="px-4 py-2 bg-surface text-text border border-border rounded-lg text-sm font-medium hover:bg-surface-elevated transition-colors">
                  Set Alert
                </button>
                <button className="px-4 py-2 bg-transparent text-muted hover:text-text text-sm font-medium transition-colors">
                  Share Forecast
                </button>
              </div>
            </div>
          </div>
        )}
    </div>
  );
};

export const OKForecastGrid: React.FC<{ 
  forecasts: OKForecast[]; 
  expandedId?: string;
  onToggle?: (id: string) => void;
  onSelectTicker?: (ticker: string) => void;
}> = ({ forecasts, expandedId, onToggle, onSelectTicker }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {forecasts.map((forecast, index) => {
        const id = forecast.id || `${forecast.ticker}-${forecast.horizon}-${index}`;
        return (
          <OKForecastCard
            key={id}
            forecast={forecast}
            expanded={expandedId === id}
            onToggle={() => onToggle?.(id)}
            onSelectTicker={onSelectTicker}
          />
        );
      })}
    </div>
  );
};

export default OKForecastCard;

