/**
 * ErrorAlert component for Finance Copilot
 * Displays error messages in a consistent, user-friendly way
 * Part of the never-empty UI strategy
 */
import React from 'react';
import { Alert as MantineAlert } from '@mantine/core';
import { IconAlertCircle as IconAlertCircle, IconRefresh as IconRefresh, IconInfoCircle as IconInfoCircle } from '@tabler/icons-react';

interface ErrorAlertProps {
  title?: string;
  message: string;
  error?: any;
  severity?: 'error' | 'warning' | 'info' | 'success';
  onReload?: () => void;
  showReload?: boolean;
  dataTestId?: string;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
  title = "Une erreur s'est produite",
  message,
  error,
  severity = 'error',
  onReload,
  showReload = true,
  dataTestId = 'error-alert'
}) => {
  // Determine color and icon based on severity
  const getColorBySeverity = () => {
    switch (severity) {
      case 'warning': return 'orange';
      case 'info': return 'blue';
      case 'success': return 'green';
      default: return 'red';
    }
  };

  const getIconBySeverity = () => {
    switch (severity) {
      case 'info': 
        return <IconInfoCircle />;
      default:
        return <IconAlertCircle />;
    }
  };

  // Format error details if available
  const errorDetails = error ? `Détails: ${typeof error === 'string' ? error : error?.message || JSON.stringify(error)}` : '';

  return (
    <MantineAlert 
      variant="outline"
      color={getColorBySeverity()}
      title={title}
      icon={getIconBySeverity()}
      data-testid={dataTestId}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <p>{message}</p>
        {errorDetails && (
          <small style={{ color: '#888', fontStyle: 'italic' }}>{errorDetails}</small>
        )}
        {showReload && onReload && (
          <button 
            onClick={onReload}
            style={{ 
              alignSelf: 'start',
              marginTop: '8px',
              padding: '6px 12px',
              backgroundColor: '#339af0',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            <IconRefresh style={{ marginRight: '4px' }} size={14} /> Rafraîchir
          </button>
        )}
      </div>
    </MantineAlert>
  );
};

export default ErrorAlert;