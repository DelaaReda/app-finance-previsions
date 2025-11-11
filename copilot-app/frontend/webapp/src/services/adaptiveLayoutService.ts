/**
 * Adaptive Layout Service
 * 
 * Interprets market context and generates optimal dashboard layout.
 * Maps priority widgets, applies default filters, and manages layout transitions.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 */

import type { MarketRegime, MarketContext } from '../hooks/useMarketContext';

/**
 * Widget identifiers that can be dynamically rendered
 */
export type WidgetId =
  | 'intelligence'
  | 'recommendations'
  | 'correlations'
  | 'forecasts'
  | 'news'
  | 'macro'
  | 'stocks'
  | 'risks'
  | 'opportunities'
  | 'alerts'
  | 'performance';

/**
 * Layout configuration for adaptive dashboard
 */
export interface AdaptiveLayoutConfig {
  topRow: WidgetId[];      // Priority widgets (most important)
  middleRow: WidgetId[];   // Secondary widgets
  bottomRow: WidgetId[];   // Tertiary widgets
  defaultFilters: Record<string, any>;
  visualPriority: 'risks' | 'opportunities' | 'balanced';
}

/**
 * Regime-specific layout presets
 * 
 * Each regime has an optimized layout that surfaces
 * the most relevant information first.
 */
const REGIME_LAYOUTS: Record<MarketRegime, AdaptiveLayoutConfig> = {
  BULL_MARKET: {
    topRow: ['intelligence', 'recommendations', 'opportunities'],
    middleRow: ['forecasts', 'news', 'stocks'],
    bottomRow: ['macro', 'performance'],
    defaultFilters: {
      direction: 'up',
      confidence_min: 0.7,
      risk_level: 'moderate',
      time_horizon: '5d',
    },
    visualPriority: 'opportunities',
  },

  BEAR_MARKET: {
    topRow: ['risks', 'intelligence', 'alerts'],
    middleRow: ['forecasts', 'correlations', 'macro'],
    bottomRow: ['news', 'performance'],
    defaultFilters: {
      direction: 'down',
      risk_level: 'high',
      time_horizon: '1d',
      defensive: true,
    },
    visualPriority: 'risks',
  },

  HIGH_VOLATILITY: {
    topRow: ['risks', 'correlations', 'alerts'],
    middleRow: ['intelligence', 'recommendations'],
    bottomRow: ['forecasts', 'news', 'macro'],
    defaultFilters: {
      risk_level: 'high',
      volatility_min: 0.3,
      time_horizon: '1d',
      hedging_focus: true,
    },
    visualPriority: 'risks',
  },

  RISK_OFF: {
    topRow: ['alerts', 'macro', 'risks'],
    middleRow: ['intelligence', 'correlations'],
    bottomRow: ['forecasts', 'news'],
    defaultFilters: {
      sector: ['Consumer Staples', 'Utilities', 'Healthcare'],
      beta_max: 0.8,
      risk_level: 'low',
      safe_havens: true,
    },
    visualPriority: 'risks',
  },

  RISK_ON: {
    topRow: ['opportunities', 'recommendations', 'intelligence'],
    middleRow: ['forecasts', 'stocks', 'performance'],
    bottomRow: ['news', 'macro'],
    defaultFilters: {
      risk_level: 'high',
      beta_min: 1.2,
      growth_focus: true,
      time_horizon: '10d',
    },
    visualPriority: 'opportunities',
  },

  CONSOLIDATION: {
    topRow: ['intelligence', 'correlations', 'forecasts'],
    middleRow: ['recommendations', 'news', 'macro'],
    bottomRow: ['stocks', 'performance'],
    defaultFilters: {
      direction: 'flat',
      range_bound: true,
      time_horizon: '5d',
    },
    visualPriority: 'balanced',
  },

  NORMAL: {
    topRow: ['intelligence', 'recommendations', 'forecasts'],
    middleRow: ['news', 'macro', 'stocks'],
    bottomRow: ['correlations', 'performance'],
    defaultFilters: {
      time_horizon: '5d',
      risk_level: 'moderate',
    },
    visualPriority: 'balanced',
  },

  UNKNOWN: {
    topRow: ['intelligence', 'forecasts', 'news'],
    middleRow: ['recommendations', 'macro', 'stocks'],
    bottomRow: ['correlations', 'performance'],
    defaultFilters: {},
    visualPriority: 'balanced',
  },
};

/**
 * Adaptive Layout Service
 */
export class AdaptiveLayoutService {
  /**
   * Get layout configuration for current market context
   */
  static getLayoutForContext(context: MarketContext): AdaptiveLayoutConfig {
    const baseLayout = REGIME_LAYOUTS[context.regime] || REGIME_LAYOUTS.NORMAL;

    // Merge with API recommendations if available
    if (context.recommended_layout) {
      return this.mergeWithRecommendations(baseLayout, context.recommended_layout);
    }

    return baseLayout;
  }

  /**
   * Merge base layout with API recommendations
   */
  private static mergeWithRecommendations(
    baseLayout: AdaptiveLayoutConfig,
    recommendations: any
  ): AdaptiveLayoutConfig {
    // If API provides priority widgets, use them
    if (recommendations.priority_widgets && recommendations.priority_widgets.length > 0) {
      return {
        ...baseLayout,
        topRow: recommendations.priority_widgets as WidgetId[],
        middleRow: recommendations.secondary_widgets || baseLayout.middleRow,
        defaultFilters: {
          ...baseLayout.defaultFilters,
          ...recommendations.filters,
        },
      };
    }

    return baseLayout;
  }

  /**
   * Get human-readable description of current layout
   */
  static getLayoutDescription(regime: MarketRegime): string {
    const descriptions: Record<MarketRegime, string> = {
      BULL_MARKET: 'Optimized for growth opportunities and momentum plays',
      BEAR_MARKET: 'Focused on risk management and defensive positioning',
      HIGH_VOLATILITY: 'Prioritizing risk assessment and hedging strategies',
      RISK_OFF: 'Highlighting safe havens and defensive sectors',
      RISK_ON: 'Emphasizing high-beta opportunities and growth sectors',
      CONSOLIDATION: 'Balanced view for range-bound markets',
      NORMAL: 'Standard balanced layout for normal market conditions',
      UNKNOWN: 'Default layout - market regime unclear',
    };

    return descriptions[regime] || descriptions.NORMAL;
  }

  /**
   * Get visual theme for regime
   */
  static getRegimeTheme(regime: MarketRegime): {
    color: string;
    icon: string;
    accentColor: string;
  } {
    const themes = {
      BULL_MARKET: { color: 'green', icon: '📈', accentColor: '#10b981' },
      BEAR_MARKET: { color: 'red', icon: '📉', accentColor: '#ef4444' },
      HIGH_VOLATILITY: { color: 'orange', icon: '⚡', accentColor: '#f97316' },
      RISK_OFF: { color: 'red', icon: '🛑', accentColor: '#dc2626' },
      RISK_ON: { color: 'green', icon: '🚀', accentColor: '#22c55e' },
      CONSOLIDATION: { color: 'blue', icon: '↔️', accentColor: '#3b82f6' },
      NORMAL: { color: 'gray', icon: '📊', accentColor: '#6b7280' },
      UNKNOWN: { color: 'gray', icon: '❓', accentColor: '#9ca3af' },
    };

    return themes[regime] || themes.NORMAL;
  }

  /**
   * Check if layout should be updated
   * (avoid unnecessary re-renders)
   */
  static shouldUpdateLayout(
    currentRegime: MarketRegime,
    newRegime: MarketRegime,
    currentConfidence: number,
    newConfidence: number
  ): boolean {
    // Always update if regime changed
    if (currentRegime !== newRegime) {
      return true;
    }

    // Update if confidence changed significantly (>0.2 delta)
    if (Math.abs(currentConfidence - newConfidence) > 0.2) {
      return true;
    }

    return false;
  }

  /**
   * Validate widget ID
   */
  static isValidWidgetId(id: string): id is WidgetId {
    const validIds: WidgetId[] = [
      'intelligence',
      'recommendations',
      'correlations',
      'forecasts',
      'news',
      'macro',
      'stocks',
      'risks',
      'opportunities',
      'alerts',
      'performance',
    ];

    return validIds.includes(id as WidgetId);
  }

  /**
   * Get default layout (fallback)
   */
  static getDefaultLayout(): AdaptiveLayoutConfig {
    return REGIME_LAYOUTS.NORMAL;
  }

  /**
   * Apply filters to widget configurations
   */
  static applyFiltersToWidgetProps(
    filters: Record<string, any>,
    widgetId: WidgetId
  ): Record<string, any> {
    // Map filters to widget-specific props
    const propMapping: Record<string, Record<string, string>> = {
      forecasts: {
        direction: 'directionFilter',
        confidence_min: 'minConfidence',
        time_horizon: 'horizon',
      },
      recommendations: {
        risk_level: 'riskLevel',
        universe: 'universe',
      },
      correlations: {
        threshold: 'threshold',
        window: 'window',
      },
      stocks: {
        sector: 'sectorFilter',
        beta_min: 'minBeta',
        beta_max: 'maxBeta',
      },
    };

    const widgetPropMap = propMapping[widgetId] || {};
    const props: Record<string, any> = {};

    Object.entries(filters).forEach(([filterKey, filterValue]) => {
      const propKey = widgetPropMap[filterKey];
      if (propKey) {
        props[propKey] = filterValue;
      }
    });

    return props;
  }
}

export default AdaptiveLayoutService;
