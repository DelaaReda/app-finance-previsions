import { useHealth } from '../../hooks/useHealth';

export function HealthIndicator() {
  const { health, loading, error } = useHealth();

  const getHealthColor = () => {
    if (loading) return '#666';
    if (error) return '#f44336';
    
    switch (health?.status) {
      case 'up': return '#4caf50';
      case 'degraded': return '#ff9800';
      case 'down': return '#f44336';
      default: return '#666';
    }
  };

  const getStatusText = () => {
    if (loading) return 'Checking...';
    if (error) return 'Error';
    
    switch (health?.status) {
      case 'up': return 'Opérationnel';
      case 'degraded': return 'Dégradé';
      case 'down': return 'Hors ligne';
      default: return 'Inconnu';
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
        Backend: {getStatusText()}
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
