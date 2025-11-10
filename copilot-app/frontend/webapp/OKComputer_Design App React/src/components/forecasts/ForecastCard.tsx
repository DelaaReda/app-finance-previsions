import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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

export interface Forecast {
  id: string;
  title: string;
  currentValue: number;
  predictedValue: number;
  confidence: number;
  timeframe: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  type: 'price' | 'percentage' | 'volume';
  rationale?: string;
  factors?: string[];
  lastUpdated: Date;
}

export interface ForecastCardProps {
  forecast: Forecast;
  className?: string;
  expanded?: boolean;
  onToggle?: () => void;
}

const trendIcons = {
  bullish: <TrendingUp className="w-4 h-4" />,
  bearish: <TrendingDown className="w-4 h-4" />,
  neutral: <Minus className="w-4 h-4" />,
};

const trendColors = {
  bullish: 'text-success',
  bearish: 'text-danger',
  neutral: 'text-muted',
};

const trendBgColors = {
  bullish: 'bg-success/10',
  bearish: 'bg-danger/10',
  neutral: 'bg-muted/10',
};

export const ForecastCard: React.FC<ForecastCardProps> = ({
  forecast,
  className,
  expanded = false,
  onToggle,
}) => {
  const [isAnimating, setIsAnimating] = useState(false);

  const predictedChange = ((forecast.predictedValue - forecast.currentValue) / forecast.currentValue) * 100;
  const isPositive = predictedChange > 0;

  const formatValue = (value: number) => {
    if (forecast.type === 'price') return formatCurrency(value);
    if (forecast.type === 'percentage') return formatPercentage(value);
    return formatNumber(value);
  };

  const confidenceColor = forecast.confidence >= 80 ? 'text-success' : 
                         forecast.confidence >= 60 ? 'text-warning' : 'text-danger';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className={cn(
        'bg-surface rounded-xl border border-border shadow-lg overflow-hidden',
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
              trendBgColors[forecast.trend]
            )}>
              <div className={trendColors[forecast.trend]}>
                {trendIcons[forecast.trend]}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-text">{forecast.title}</h3>
              <p className="text-sm text-muted">{forecast.timeframe}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className={cn('flex items-center gap-1 text-sm font-medium', confidenceColor)}>
              <Target className="w-4 h-4" />
              {forecast.confidence}% confidence
            </div>
          </div>
        </div>

        {/* Values */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <p className="text-sm text-muted mb-1">Current</p>
            <p className="text-xl font-bold text-text">{formatValue(forecast.currentValue)}</p>
          </div>
          <div>
            <p className="text-sm text-muted mb-1">Predicted</p>
            <p className="text-xl font-bold text-primary">{formatValue(forecast.predictedValue)}</p>
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
          <motion.div
            className={cn('h-2 rounded-full', 
              forecast.confidence >= 80 ? 'bg-success' :
              forecast.confidence >= 60 ? 'bg-warning' : 'bg-danger'
            )}
            initial={{ width: 0 }}
            animate={{ width: `${forecast.confidence}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </div>

        {/* Footer info */}
        <div className="flex items-center justify-between text-sm text-muted">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              Last updated: {new Date(forecast.lastUpdated).toLocaleDateString()}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <span>Click to expand</span>
            <motion.div
              animate={{ rotate: expanded ? 180 : 0 }}
              transition={{ duration: 0.3 }}
            >
              <ArrowRight className="w-4 h-4" />
            </motion.div>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="border-t border-border"
          >
            <div className="p-6 space-y-6">
              {/* Rationale */}
              {forecast.rationale && (
                <div>
                  <h4 className="text-sm font-semibold text-text mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-primary" />
                    Analysis Rationale
                  </h4>
                  <p className="text-sm text-muted leading-relaxed">{forecast.rationale}</p>
                </div>
              )}

              {/* Key Factors */}
              {forecast.factors && forecast.factors.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-success" />
                    Key Factors
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {forecast.factors.map((factor, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center gap-2 text-sm text-muted"
                      >
                        <div className="w-1.5 h-1.5 bg-primary rounded-full" />
                        {factor}
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-3 pt-4 border-t border-border">
                <button className="px-4 py-2 bg-primary text-white rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
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
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export const ForecastGrid: React.FC<{ 
  forecasts: Forecast[]; 
  expandedId?: string;
  onToggle?: (id: string) => void;
}> = ({ forecasts, expandedId, onToggle }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {forecasts.map((forecast) => (
        <ForecastCard
          key={forecast.id}
          forecast={forecast}
          expanded={expandedId === forecast.id}
          onToggle={() => onToggle?.(forecast.id)}
        />
      ))}
    </div>
  );
};

export default ForecastCard;