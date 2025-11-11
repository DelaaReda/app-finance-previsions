/**
 * Global Error Boundary Component
 * Catches JavaScript errors anywhere in the child component tree, logs those errors,
 * and displays a fallback UI instead of the component tree that crashed.
 */

import React, { Component, ErrorInfo } from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error to an error reporting service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // In a real app, you might send this to a logging service
    // Example: 
    // logger.error('React Error Boundary', { error: error.toString(), errorInfo, componentStack: errorInfo.componentStack });
    
    // Update state with error info
    this.setState({ errorInfo });
  }

  handleReset = () => {
    // Reset the error state to try rendering the children again
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
    // Optionally trigger a refresh or navigation
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div style={styles.container}>
          <div style={styles.content}>
            <h2 style={styles.title}>🚨 Une erreur est survenue</h2>
            <p style={styles.message}>
              {this.state.error?.message || 'Une erreur inconnue est survenue.'}
            </p>
            <p style={styles.helpText}>
              Le service est conscient de ce problème. Essayez de rafraîchir.
            </p>
            <div style={styles.buttonContainer}>
              <button 
                onClick={this.handleReset}
                style={styles.refreshButton}
              >
                Rafraîchir
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && (
              <details style={styles.details}>
                <summary style={styles.summary}>Détails techniques</summary>
                <pre style={styles.pre}>
                  {this.state.error && this.state.error.toString()}
                  {'\n'}
                  {this.state.errorInfo?.componentStack}
                </pre>
              </details>
            )}
            <div style={styles.footer}>
              ID: {Math.random().toString(36).substring(2, 8).toUpperCase()}
              {' • '}
              {new Date().toLocaleString('fr-FR')}
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5',
    fontFamily: 'system-ui, -apple-system, sans-serif',
    padding: '20px',
  } as React.CSSProperties,
  
  content: {
    maxWidth: '500px',
    width: '100%',
    padding: '40px',
    backgroundColor: 'white',
    borderRadius: '12px',
    boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
    textAlign: 'center' as const,
  },
  
  title: {
    margin: '0 0 16px',
    fontSize: '24px',
    fontWeight: '600',
    color: '#d32f2f',
  },
  
  message: {
    margin: '0 0 16px',
    fontSize: '16px',
    color: '#555',
    lineHeight: '1.5',
  },
  
  helpText: {
    margin: '0 0 24px',
    fontSize: '14px',
    color: '#888',
    lineHeight: '1.4',
  },
  
  buttonContainer: {
    marginBottom: '24px',
  },
  
  refreshButton: {
    padding: '12px 24px',
    backgroundColor: '#1976d2',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    fontSize: '16px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  
  details: {
    marginTop: '20px',
    textAlign: 'left' as const,
    fontSize: '12px',
    color: '#666',
    backgroundColor: '#fafafa',
    padding: '10px',
    borderRadius: '4px',
    overflow: 'auto',
    maxHeight: '200px',
  },
  
  summary: {
    cursor: 'pointer',
    fontWeight: '600',
    marginBottom: '8px',
    color: '#d32f2f',
  },
  
  pre: {
    margin: 0,
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
  },
  
  footer: {
    fontSize: '12px',
    color: '#999',
    marginTop: '24px',
    borderTop: '1px solid #eee',
    paddingTop: '16px',
  },
};

export default GlobalErrorBoundary;