import { Badge } from '@mantine/core';
import type { MarketRegime } from '../../hooks/useMarketContext';

interface RegimeBadgeProps {
  regime: MarketRegime;
  confidence: number;
}

/**
 * Get badge color based on market regime
 */
function getRegimeColor(regime: MarketRegime): string {
  const colorMap: Record<MarketRegime, string> = {
    HIGH_VOLATILITY: 'red',
    ELEVATED_RISK: 'orange',
    BEAR_MARKET: 'red',
    RISK_OFF: 'orange',
    NORMAL: 'blue',
    RISK_ON: 'green',
    BULL_MARKET: 'green',
  };
  return colorMap[regime] || 'gray';
}

/**
 * Format regime text for display
 */
function formatRegime(regime: MarketRegime): string {
  return regime
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ');
}

/**
 * RegimeBadge Component
 * 
 * Displays the current market regime with confidence score
 * Color-coded for quick visual recognition
 * 
 * @param regime - Market regime classification
 * @param confidence - Confidence score (0-1)
 */
export function RegimeBadge({ regime, confidence }: RegimeBadgeProps) {
  const color = getRegimeColor(regime);
  const displayText = formatRegime(regime);
  const confidencePercent = Math.round(confidence * 100);

  return (
    <Badge
      color={color}
      size="lg"
      variant="filled"
      styles={{
        root: {
          fontSize: '1rem',
          fontWeight: 600,
          padding: '0.75rem 1rem',
          textTransform: 'none',
        },
      }}
    >
      {displayText} • {confidencePercent}% confidence
    </Badge>
  );
}
