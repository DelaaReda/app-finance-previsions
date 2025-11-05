import { useState, useEffect } from 'react';
import { apiGet } from '../../api/client';

interface HealthStatus {
  status: 'up' | 'down' | 'degraded';
  lastChecked: string | null;
  lastUpdate: string | null;
}

export function HealthIndicator() {
  const [health, setHealth] = useState<HealthStatus>({ 
    status: 'down', 
    lastChecked: null, 
    lastUpdate: null 
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await apiGet('/health');
        if (response.ok && response.data) {
          const data: any = response.data;
            const isUp = data.status === 'up' && data.backend_up !== false;
            const lastUpdate = data.last_updates?.forecasts || data.timestamp || null;
          
          setHealth({
            status: isUp ? 'up' : 'down',
            lastChecked: new Date().toISOString(),
            lastUpdate: lastUpdate
          });
        } else {
          setHealth({ status: 'down', lastChecked: new Date().toISOString(), lastUpdate: null });
        }
      } catch (error) {
        setHealth({ status: 'down', lastChecked: new Date().toISOString(), lastUpdate: null });
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchHealth();

    // Refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);

    return () => clearInterval(interval);
  }, []);

  const getHealthColor = () => {
    switch (health.status) {
      case 'up': return '#4caf50';
      case 'degraded': return '#ff9800';
      case 'down': return '#f44336';
      default: return '#666';
    }
  };

  return (
    <div style={styles.healthContainer}>
      <div 
        style={{ 
          ...styles.healthIndicator, 
          backgroundColor: getHealthColor(),
          width: loading ? 'auto' : '12px',
          height: loading ? 'auto' : '12px',
        }} 
      >
        {loading && (
          <span style={styles.loadingText}>...</span>
        )}
      </div>
      <span style={styles.healthText}>
        Backend: {health.status === 'up' ? 'Opérationnel' : health.status === 'degraded' ? 'Dégradé' : 'Hors ligne'}
      </span>
    </div>
  );
}

const styles = {
  healthContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 8px',
    borderRadius: '4px',
    backgroundColor: '#222',
  } as React.CSSProperties,
  healthIndicator: {
    borderRadius: '50%',
    minWidth: '12px',
    minHeight: '12px',
  } as React.CSSProperties,
  loadingText: {
    fontSize: '10px',
    color: '#fff',
  } as React.CSSProperties,
  healthText: {
    fontSize: '12px',
    color: '#aaa',
  } as React.CSSProperties,
};