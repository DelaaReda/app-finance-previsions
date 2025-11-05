import { useEffect, useState } from 'react';

interface HealthStatus {
  status: string;
  backend_up: boolean;
  last_updates: Record<string, number>;
  data_paths: Record<string, string>;
  timestamp: number;
}

export function HealthStatusBadge() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch('/api/health');
        const result = await response.json();
        
        if (result.ok) {
          setHealth(result.data);
        } else {
          setError('Health check failed');
        }
      } catch (err) {
        setError('Network error');
        console.error('Health check error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-800">
        Checking...
      </span>
    );
  }

  if (error || !health) {
    return (
      <span className="px-2 py-1 rounded text-xs font-medium bg-red-100 text-red-800" title={error || 'Health data unavailable'}>
        Error
      </span>
    );
  }

  // Determine overall status based on health data
  const isHealthy = health.backend_up;
  let statusColor = 'bg-green-100 text-green-800';
  let statusText = 'Healthy';

  if (!isHealthy) {
    statusColor = 'bg-red-100 text-red-800';
    statusText = 'Unhealthy';
  } else if (health.last_updates && Object.keys(health.last_updates).length === 0) {
    statusColor = 'bg-yellow-100 text-yellow-800';
    statusText = 'Limited';
  }

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${statusColor}`} title={`Backend: ${health.status}`}>
      {statusText}
    </span>
  );
}