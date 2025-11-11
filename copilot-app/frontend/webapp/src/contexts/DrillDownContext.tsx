/**
 * DrillDown Context
 * 
 * Manages intelligent navigation from widgets to detail pages.
 * Preserves context (source, reason, regime) for smart back navigation.
 * 
 * Author: ELENA-39
 * Task: FC-INT-027
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import type { MarketRegime } from '../hooks/useMarketContext';

/**
 * Source of drill-down navigation
 */
export type DrillDownSource =
  | 'recommendations'
  | 'forecasts'
  | 'intelligence'
  | 'correlations'
  | 'news'
  | 'opportunities'
  | 'risks'
  | 'dashboard'
  | 'unknown';

/**
 * Metadata about why user navigated here
 */
export interface DrillDownMetadata {
  source: DrillDownSource;
  reason?: string;
  regime?: MarketRegime;
  additionalData?: Record<string, any>;
}

/**
 * Current drill-down state
 */
export interface DrillDownState {
  ticker: string;
  source: DrillDownSource;
  reason?: string;
  regime?: MarketRegime;
  additionalData?: Record<string, any>;
  timestamp: string;
  previousUrl: string;
}

/**
 * Context value
 */
interface DrillDownContextValue {
  // Current state
  currentDrillDown: DrillDownState | null;
  
  // Navigation methods
  navigateToTicker: (ticker: string, metadata?: Partial<DrillDownMetadata>) => void;
  navigateToForecast: (ticker: string, metadata?: Partial<DrillDownMetadata>) => void;
  navigateToNews: (articleId: string, ticker?: string, metadata?: Partial<DrillDownMetadata>) => void;
  
  // History methods
  goBack: () => void;
  clearContext: () => void;
  
  // Helpers
  getContextDescription: () => string;
  hasContext: boolean;
}

const DrillDownContext = createContext<DrillDownContextValue | undefined>(undefined);

/**
 * DrillDownProvider
 * 
 * Wraps the app to provide drill-down navigation context.
 */
export function DrillDownProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  
  const [currentDrillDown, setCurrentDrillDown] = useState<DrillDownState | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  
  /**
   * Navigate to ticker detail page
   */
  const navigateToTicker = useCallback((
    ticker: string,
    metadata?: Partial<DrillDownMetadata>
  ) => {
    const state: DrillDownState = {
      ticker,
      source: metadata?.source || 'unknown',
      reason: metadata?.reason,
      regime: metadata?.regime,
      additionalData: metadata?.additionalData,
      timestamp: new Date().toISOString(),
      previousUrl: location.pathname,
    };
    
    setCurrentDrillDown(state);
    setHistory((prev) => [...prev, location.pathname]);
    
    // Navigate with state
    navigate(`/ticker/${ticker}`, { state });
  }, [navigate, location]);
  
  /**
   * Navigate to forecast detail (redirects to ticker with forecast context)
   */
  const navigateToForecast = useCallback((
    ticker: string,
    metadata?: Partial<DrillDownMetadata>
  ) => {
    navigateToTicker(ticker, {
      ...metadata,
      source: metadata?.source || 'forecasts',
    });
  }, [navigateToTicker]);
  
  /**
   * Navigate to news detail (future implementation)
   */
  const navigateToNews = useCallback((
    articleId: string,
    ticker?: string,
    metadata?: Partial<DrillDownMetadata>
  ) => {
    // For now, navigate to ticker if available
    if (ticker) {
      navigateToTicker(ticker, {
        ...metadata,
        source: 'news',
        additionalData: { articleId, ...metadata?.additionalData },
      });
    }
  }, [navigateToTicker]);
  
  /**
   * Go back to previous page (smart back)
   */
  const goBack = useCallback(() => {
    if (history.length > 0) {
      const previousUrl = history[history.length - 1];
      setHistory((prev) => prev.slice(0, -1));
      navigate(previousUrl);
      setCurrentDrillDown(null);
    } else {
      // Fallback to browser back
      navigate(-1);
      setCurrentDrillDown(null);
    }
  }, [history, navigate]);
  
  /**
   * Clear drill-down context
   */
  const clearContext = useCallback(() => {
    setCurrentDrillDown(null);
    setHistory([]);
  }, []);
  
  /**
   * Get human-readable context description
   */
  const getContextDescription = useCallback((): string => {
    if (!currentDrillDown) return '';
    
    const sourceLabels: Record<DrillDownSource, string> = {
      recommendations: 'Daily Recommendations',
      forecasts: 'Forecasts',
      intelligence: 'Intelligence Dashboard',
      correlations: 'Correlation Analysis',
      news: 'News Feed',
      opportunities: 'Opportunities',
      risks: 'Risk Analysis',
      dashboard: 'Dashboard',
      unknown: 'Previous Page',
    };
    
    const sourceLabel = sourceLabels[currentDrillDown.source];
    
    if (currentDrillDown.reason) {
      return `From ${sourceLabel}: ${currentDrillDown.reason}`;
    }
    
    return `From ${sourceLabel}`;
  }, [currentDrillDown]);
  
  const value: DrillDownContextValue = {
    currentDrillDown,
    navigateToTicker,
    navigateToForecast,
    navigateToNews,
    goBack,
    clearContext,
    getContextDescription,
    hasContext: currentDrillDown !== null,
  };
  
  return (
    <DrillDownContext.Provider value={value}>
      {children}
    </DrillDownContext.Provider>
  );
}

/**
 * useDrillDown Hook
 * 
 * Access drill-down context from any component.
 */
export function useDrillDown() {
  const context = useContext(DrillDownContext);
  
  if (context === undefined) {
    throw new Error('useDrillDown must be used within DrillDownProvider');
  }
  
  return context;
}

export default DrillDownContext;
