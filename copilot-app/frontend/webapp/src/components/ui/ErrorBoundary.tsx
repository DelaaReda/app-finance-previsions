import React from 'react';
import { Alert, AlertTitle, Button } from '@mui/material';

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

// Type for react-error-boundary fallback props
interface FallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

export function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
  return (
    <Alert severity="error" sx={{ my: 2 }}>
      <AlertTitle>Une erreur est survenue</AlertTitle>
      {String(error?.message || error)}
      <Button sx={{ ml: 2 }} onClick={resetErrorBoundary} variant="outlined">Réessayer</Button>
    </Alert>
  );
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Alert severity="error" sx={{ my: 2 }}>
          <AlertTitle>Une erreur est survenue</AlertTitle>
          {this.state.error?.message || 'Erreur inconnue'}
          <Button sx={{ ml: 2 }} onClick={this.resetError} variant="outlined">Réessayer</Button>
        </Alert>
      );
    }

    return this.props.children;
  }
}