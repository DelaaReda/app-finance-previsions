/**
 * Fully Unified Health Component that replaces both HealthIndicator and HealthStatusBadge
 * Consumes unified apiGet client that unwraps {ok, data} envelope
 * Provides both visual indicator and badge status in one component
 */

import React from 'react';
import { Chip } from '@mui/material';
import { useHealth } from '../../hooks/useHealth';

interface UnifiedHealthProps {
  variant?: 'indicator' | 'badge';  // Determines the display type
  showStatusText?: boolean;        // Whether to show status text alongside indicator
  size?: 'small' | 'medium';       // Size of the component
  compact?: boolean;               // More compact version
}

export function UnifiedHealth({ 
  variant = 'badge', 
  showStatusText = true, 
  size = 'small',
  compact = false
}: UnifiedHealthProps) {
  const { health, loading, error, lastChecked } = useHealth();

  // Handle loading state
  if (loading) {
    if (variant === 'indicator') {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: compact ? '4px' : '6px' }}>
          <div 
            style={{ 
              width: '10px', 
              height: '10px', 
              borderRadius: '50%', 
              backgroundColor: '#666',
              animation: 'pulse 1.5s ease-in-out infinite'
            }} 
          />
          {showStatusText && <span style={{ fontSize: '12px', color: '#aaa' }}>Checking...</span>}
        </div>
      );
    } else {
      return <Chip label="Checking..." size={size} variant="outlined" />;
    }
  }

  // Handle error state
  if (error || !health) {
    if (variant === 'indicator') {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: compact ? '4px' : '6px' }}>
          <div 
            style={{ 
              width: '10px', 
              height: '10px', 
              borderRadius: '50%', 
              backgroundColor: '#f44336',
            }} 
          />
          {showStatusText && <span style={{ fontSize: '12px', color: '#f44336' }}>Error</span>}
        </div>
      );
    } else {
      return (
        <Chip 
          label="Error" 
          size={size} 
          color="error" 
          variant="outlined"
          title={error || 'Health data unavailable'}
        />
      );
    }
  }

  // Determine status and color
  const status = health.status;
  let statusColor = 'default';
  let statusText = '';

  switch (status) {
    case 'up':
      statusColor = 'success';
      statusText = 'Healthy';
      break;
    case 'degraded':
      statusColor = 'warning';
      statusText = 'Degraded';
      break;
    case 'down':
      statusColor = 'error';
      statusText = 'Down';
      break;
    default:
      statusColor = 'default';
      statusText = 'Unknown';
  }

  // Create detailed title
  let title = `Status: ${statusText}`;
  if (health.timestamp) {
    title += `\nLast update: ${new Date(health.timestamp).toLocaleString()}`;
  } else if (lastChecked) {
    title += `\nChecked: ${new Date(lastChecked).toLocaleString()}`;
  }
  if (health.message) {
    title += `\nMessage: ${health.message}`;
  }

  // Render based on variant
  if (variant === 'indicator') {
    const colorMap: Record<string, string> = {
      'success': '#4caf50',
      'warning': '#ff9800',
      'error': '#f44336',
      'default': '#666'
    };

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: compact ? '4px' : '6px' }}>
        <div 
          style={{ 
            width: '10px', 
            height: '10px', 
            borderRadius: '50%', 
            backgroundColor: colorMap[statusColor] || colorMap['default'],
          }} 
        />
        {showStatusText && <span style={{ fontSize: '12px', color: colorMap[statusColor] || '#666' }}>
          {health.backend_up || status === 'up' ? 'Opérationnel' : 
           status === 'degraded' ? 'Dégradé' : 
           'Hors ligne'}
        </span>}
      </div>
    );
  } else {
    // For badge variant
    const muiColor: "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" = 
      statusColor as "success" | "warning" | "error" | "default";
    
    return (
      <Chip 
        label={showStatusText ? statusText : undefined} 
        size={size}
        color={muiColor}
        variant="outlined"
        title={title}
      />
    );
  }
}