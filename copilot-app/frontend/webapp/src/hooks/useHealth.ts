import { useState, useEffect } from 'react';
import { apiGet } from '../api/client';

export interface HealthData {
  status: 'up' | 'down' | 'degraded';
  backend_up?: boolean;
  last_updates?: Record<string, string>;
  data_paths?: Record<string, string>;
  timestamp?: string;
  version?: string;
  message?: string;
  error?: string;
}

export interface HealthHookReturn {
  health: HealthData | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  lastChecked: string | null;
}

/**
 * Custom hook to fetch and manage health status of the Finance Copilot backend
 * Unifies the functionality of HealthIndicator and HealthStatusBadge components
 * @returns Health status, loading state, error state, and refresh function
 */
export function useHealth(): HealthHookReturn {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const fetchHealth = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      // Use the unified apiGet client that handles the { ok, data } envelope
      const response = await apiGet<HealthData>('/health');
      
      if (response.ok && response.data) {
        const data: HealthData = response.data;
        
        // Standardize the status based on backend_up and other health indicators
        let standardizedStatus: 'up' | 'down' | 'degraded' = 'down';
        if (data.backend_up === true || data.status === 'up') {
          standardizedStatus = 'up';
        } else if (data.status === 'degraded' || (data.status !== 'down' && data.backend_up !== false)) {
          standardizedStatus = 'degraded';
        }
        
        // Update state with proper health data
        setHealth({
          ...data,
          status: standardizedStatus
        });
      } else {
        // Handle error response from API
        const errorMsg = response.error || 'Réponse API inattendue';
        setError(errorMsg);
        setHealth({
          status: 'down',
          error: errorMsg
        });
      }
      
      setLastChecked(new Date().toISOString());
    } catch (err: any) {
      // Handle network/transport errors
      const errorMessage = err.message || 'Erreur de chargement du statut de santé';
      setError(errorMessage);
      setHealth({
        status: 'down',
        error: errorMessage
      });
      setLastChecked(new Date().toISOString());
    } finally {
      setLoading(false);
    }
  };

  // Fetch health on mount
  useEffect(() => {
    fetchHealth();
    
    // Set up refresh interval (every 30 seconds)
    const interval = setInterval(fetchHealth, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return {
    health,
    loading,
    error,
    refresh: fetchHealth,
    lastChecked
  };
}
