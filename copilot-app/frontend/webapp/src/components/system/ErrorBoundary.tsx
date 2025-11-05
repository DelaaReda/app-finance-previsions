import React, { Component, ReactNode } from 'react';
import { Alert, Button, Container, Typography, Box, Card, CardContent } from '@mui/material';
import { Refresh as RefreshIcon, WarningAmberOutlined as WarningIcon } from '@mui/icons-material';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by ErrorBoundary:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    // Reset the error state to allow the app to recover
    window.location.reload(); // Simple solution: reload the app
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Card sx={{ boxShadow: 3 }}>
            <CardContent>
              <Box textAlign="center" py={4}>
                <WarningIcon color="error" fontSize="large" sx={{ fontSize: 60, mb: 2 }} />
                <Typography variant="h5" component="h2" gutterBottom color="error">
                  Une erreur inattendue s'est produite
                </Typography>
                
                {this.state.error && (
                  <Typography variant="body1" color="text.secondary" gutterBottom>
                    {this.state.error.message}
                  </Typography>
                )}
                
                {this.state.errorInfo && (
                  <Alert severity="info" sx={{ textAlign: 'left', mt: 2 }}>
                    <Typography variant="caption" component="div" fontFamily="monospace" whiteSpace="pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </Typography>
                  </Alert>
                )}
                
                <Box sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<RefreshIcon />}
                    onClick={this.handleRetry}
                    size="large"
                  >
                    Relancer l'application
                  </Button>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Container>
      );
    }

    return this.props.children;
  }
}

export { ErrorBoundary };