import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, client } from '../api/client';
import { validateData, HealthSchema, logValidationSuccess } from '@/lib/zodWrapper';

export interface LegacyHealthData {
  status: 'up' | 'down' | 'degraded';
  backend_up?: boolean;
  last_updates?: Record<string, string>;
  data_paths?: Record<string, string>;
  timestamp?: string;
  version?: string;
  message?: string;
  error?: string;
}

export interface LegacyHealthHookReturn {
  health: LegacyHealthData | null;
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
export function useLegacyHealth(): LegacyHealthHookReturn {
  const [health, setHealth] = useState<LegacyHealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<string | null>(null);

  const fetchHealth = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    
    try {
      // Use the unified apiGet client that handles the { ok, data } envelope
      const response = await apiGet<LegacyHealthData>('/api/health');
      
      if (response.ok && response.data) {
        const data: LegacyHealthData = response.data;
        
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

export type DatasetHealth = {
  name: string;
  last_update: string;
  latency_sec: number;
  errors_24h: number;
};

export type Health = {
  updated_at?: string;
  datasets: DatasetHealth[];
  thresholds?: { stale_sec?: Record<string, number> };
};

export function useHealth() {
  return useQuery<Health>({
    queryKey: ['health-datasets'],
    queryFn: async () => {
      const raw = await client.get<LegacyHealthData>('/api/health');
      const now = Date.now();
      const datasets: DatasetHealth[] = Object.entries(raw.last_updates ?? {}).map(([name, iso]) => {
        const lastUpdateMs = iso ? Date.parse(iso) : NaN;
        const latencySec = Number.isFinite(lastUpdateMs)
          ? Math.max(0, Math.round((now - lastUpdateMs) / 1000))
          : 86_400; // 24h par défaut si date inconnue
        return {
          name,
          last_update: iso ?? 'inconnu',
          latency_sec: latencySec,
          errors_24h: 0,
        };
      });

      const response: Health = {
        updated_at: raw.timestamp ?? new Date().toISOString(),
        datasets,
        thresholds: {
          stale_sec: datasets.reduce<Record<string, number>>((acc, dataset) => {
            acc[dataset.name] = 3600; // 1h par défaut
            return acc;
          }, {}),
        },
      }

      try {
        const validated = validateData(response, HealthSchema);
        logValidationSuccess('Health', validated.datasets.length);
        return validated;
      } catch (error) {
        console.warn('[useHealth] Schema mismatch, returning unvalidated payload', error);
        return response;
      }
    },
    refetchInterval: 60_000,
  });
}
