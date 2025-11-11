/**
 * Adaptive Layout Context
 * 
 * Provides adaptive layout state and controls to the dashboard.
 * Manages automatic/manual mode switching and layout updates.
 * 
 * Author: ELENA-39
 * Task: FC-INT-026
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { useMarketContext, type MarketRegime } from '../hooks/useMarketContext';
import { AdaptiveLayoutService, type AdaptiveLayoutConfig, type WidgetId } from '../services/adaptiveLayoutService';

interface AdaptiveLayoutContextValue {
  // Current state
  currentRegime: MarketRegime;
  currentLayout: AdaptiveLayoutConfig;
  confidence: number;
  
  // Mode control
  isManualMode: boolean;
  toggleMode: () => void;
  enableAutoMode: () => void;
  enableManualMode: () => void;
  
  // Layout control
  refreshLayout: () => void;
  customizeLayout: (layout: Partial<AdaptiveLayoutConfig>) => void;
  resetLayout: () => void;
  
  // Status
  isLoading: boolean;
  error: Error | null;
  
  // Metadata
  layoutDescription: string;
  regimeTheme: {
    color: string;
    icon: string;
    accentColor: string;
  };
}

const AdaptiveLayoutContext = createContext<AdaptiveLayoutContextValue | undefined>(undefined);

/**
 * AdaptiveLayoutProvider
 * 
 * Wraps the dashboard and provides adaptive layout functionality.
 */
export function AdaptiveLayoutProvider({ children }: { children: ReactNode }) {
  const { data: marketContext, isLoading, error: contextError, refetch } = useMarketContext();
  
  // State
  const [isManualMode, setIsManualMode] = useState(false);
  const [customLayout, setCustomLayout] = useState<AdaptiveLayoutConfig | null>(null);
  const [previousRegime, setPreviousRegime] = useState<MarketRegime>('NORMAL');
  
  // Derive current regime and confidence
  const currentRegime = marketContext?.regime || 'NORMAL';
  const confidence = marketContext?.confidence || 0;
  
  // Generate layout
  const currentLayout = isManualMode && customLayout
    ? customLayout
    : marketContext
    ? AdaptiveLayoutService.getLayoutForContext(marketContext)
    : AdaptiveLayoutService.getDefaultLayout();
  
  // Get metadata
  const layoutDescription = AdaptiveLayoutService.getLayoutDescription(currentRegime);
  const regimeTheme = AdaptiveLayoutService.getRegimeTheme(currentRegime);
  
  // Auto-update layout when regime changes (if in auto mode)
  useEffect(() => {
    if (isManualMode) return;
    
    const shouldUpdate = AdaptiveLayoutService.shouldUpdateLayout(
      previousRegime,
      currentRegime,
      0, // We don't track previous confidence for now
      confidence
    );
    
    if (shouldUpdate) {
      setPreviousRegime(currentRegime);
      // Layout will auto-update via derived state
    }
  }, [currentRegime, confidence, isManualMode, previousRegime]);
  
  // Mode controls
  const toggleMode = useCallback(() => {
    setIsManualMode((prev) => !prev);
  }, []);
  
  const enableAutoMode = useCallback(() => {
    setIsManualMode(false);
    setCustomLayout(null);
  }, []);
  
  const enableManualMode = useCallback(() => {
    setIsManualMode(true);
  }, []);
  
  // Layout controls
  const refreshLayout = useCallback(() => {
    refetch();
  }, [refetch]);
  
  const customizeLayout = useCallback((layout: Partial<AdaptiveLayoutConfig>) => {
    setCustomLayout((prev) => ({
      ...(prev || AdaptiveLayoutService.getDefaultLayout()),
      ...layout,
    }));
    setIsManualMode(true);
  }, []);
  
  const resetLayout = useCallback(() => {
    setCustomLayout(null);
    setIsManualMode(false);
  }, []);
  
  const value: AdaptiveLayoutContextValue = {
    currentRegime,
    currentLayout,
    confidence,
    isManualMode,
    toggleMode,
    enableAutoMode,
    enableManualMode,
    refreshLayout,
    customizeLayout,
    resetLayout,
    isLoading,
    error: contextError instanceof Error ? contextError : null,
    layoutDescription,
    regimeTheme,
  };
  
  return (
    <AdaptiveLayoutContext.Provider value={value}>
      {children}
    </AdaptiveLayoutContext.Provider>
  );
}

/**
 * useAdaptiveLayout Hook
 * 
 * Access adaptive layout context from any child component.
 */
export function useAdaptiveLayout() {
  const context = useContext(AdaptiveLayoutContext);
  
  if (context === undefined) {
    throw new Error('useAdaptiveLayout must be used within AdaptiveLayoutProvider');
  }
  
  return context;
}

export default AdaptiveLayoutContext;
