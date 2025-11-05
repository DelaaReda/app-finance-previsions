import React from 'react';
import { 
  Container, 
  Typography, 
  Paper, 
  Box, 
  Grid, 
  Chip, 
  LinearProgress, 
  Alert, 
  Button,
  Card,
  CardContent
} from '@mui/material';
import { 
  CheckCircle as CheckCircleIcon, 
  Warning as WarningIcon, 
  Error as ErrorIcon
} from '@mui/icons-material';

const UIValidationDashboard: React.FC = () => {
  // Mock validation data - in a real implementation this would come from validation API
  const validationData = {
    components_migrated: 42,
    total_components: 45,
    migration_percentage: 93.3,
    accessibility_score: 98,
    performance_score: 95,
    bundle_size_increase: '12kb',
    passed_tests: 245,
    total_tests: 250,
    test_coverage: 98,
    issues_found: [
      { id: 1, component: 'Backtests.tsx', issue: 'Non-MUI table component', severity: 'medium' },
      { id: 2, component: 'Backtests.tsx', issue: 'Missing error boundary', severity: 'low' },
      { id: 3, component: 'Stocks.tsx', issue: 'Legacy CSS classes', severity: 'low' },
    ],
    validated_pages: [
      { name: 'Dashboard', status: 'valid', components: 8 },
      { name: 'Forecasts', status: 'valid', components: 12 },
      { name: 'News', status: 'valid', components: 10 },
      { name: 'Macro', status: 'valid', components: 7 },
      { name: 'Backtests', status: 'partial', components: 5 },
      { name: 'Brief', status: 'valid', components: 6 },
      { name: 'Stocks', status: 'partial', components: 4 },
      { name: 'Copilot', status: 'valid', components: 3 },
    ]
  };

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'valid': return 'success';
      case 'partial': return 'warning';
      case 'invalid': return 'error';
      default: return 'default';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch(severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'info';
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Validation UI - Migration Complète
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary" gutterBottom>
                Composants Migrés
              </Typography>
              <Typography variant="h4">
                {validationData.components_migrated}/{validationData.total_components}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={validationData.migration_percentage} 
                  sx={{ width: '100%', mr: 1 }} 
                />
                <Typography variant="caption">{validationData.migration_percentage.toFixed(1)}%</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary" gutterBottom>
                Score Accessibilité  
              </Typography>
              <Typography variant="h4">{validationData.accessibility_score}%</Typography>
              <Chip 
                label="WCAG 2.1 AA" 
                color="success" 
                variant="outlined" 
                sx={{ mt: 1 }} 
              />
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary" gutterBottom>
                Score Performance
              </Typography>
              <Typography variant="h4">{validationData.performance_score}%</Typography>
              <Chip 
                label="Lighthouse A" 
                color="success" 
                variant="outlined" 
                sx={{ mt: 1 }} 
              />
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" color="textSecondary" gutterBottom>
                Tests Passés
              </Typography>
              <Typography variant="h4">
                {validationData.passed_tests}/{validationData.total_tests}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                <LinearProgress 
                  variant="determinate" 
                  value={(validationData.passed_tests / validationData.total_tests) * 100} 
                  sx={{ width: '100%', mr: 1 }} 
                />
                <Typography variant="caption">{validationData.test_coverage}%</Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Pages Validées
            </Typography>
            <Grid container spacing={2}>
              {validationData.validated_pages.map((page) => (
                <Grid item xs={6} sm={4} md={3} key={page.name}>
                  <Card variant="outlined" sx={{ height: '100%', border: `2px solid ${
                      page.status === 'valid' ? '#4caf50' : 
                      page.status === 'partial' ? '#ff9800' : 
                      '#f44336'
                    }` }}>
                    <CardContent>
                      <Typography variant="subtitle1" component="div">
                        {page.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {page.components} composants
                      </Typography>
                      <Chip
                        label={page.status.charAt(0).toUpperCase() + page.status.slice(1)}
                        color={getStatusColor(page.status) as 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'}
                        size="small"
                        sx={{ mt: 1 }}
                      />
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
          
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Problèmes Détectés
            </Typography>
            {validationData.issues_found.length > 0 ? (
              <Box>
                {validationData.issues_found.map((issue) => (
                  <Alert 
                    key={issue.id} 
                    severity={getSeverityColor(issue.severity) as 'error' | 'warning' | 'info' | 'success'}
                    sx={{ mb: 1 }}
                  >
                    <strong>{issue.component}</strong>: {issue.issue} 
                    <Chip 
                      label={issue.severity.toUpperCase()} 
                      size="small" 
                      sx={{ ml: 1 }} 
                      color={getSeverityColor(issue.severity) as 'error' | 'warning' | 'info' | 'success'}
                    />
                  </Alert>
                ))}
              </Box>
            ) : (
              <Alert severity="success">
                Aucun problème détecté ! Migration UI complète avec succès.
              </Alert>
            )}
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="h6" gutterBottom>
              Résumé de la Migration
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Validation complète de la migration UI vers Material UI. Tous les composants critiques 
              ont été migrés avec succès, améliorant ainsi la cohérence visuelle, l'accessibilité et 
              la performance de l'application.
            </Typography>
            
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
              Métriques Principales:
            </Typography>
            <ul>
              <li>Bundle size: +{validationData.bundle_size_increase} (optimisé)</li>
              <li>Temps de chargement moyen: &lt; 2.5s</li>
              <li>Score Lighthouse: {validationData.performance_score}/100</li>
              <li>Accessibilité: WCAG 2.1 AA</li>
              <li>Couverture des tests: {validationData.test_coverage}%</li>
            </ul>
            
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Button variant="contained" color="primary">
                Télécharger le Rapport Complet
              </Button>
            </Box>
          </Paper>
          
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Actions Recommandées
            </Typography>
            <ul>
              <li>Migrer les 3 composants restants</li>
              <li>Ajouter un ErrorBoundary à Backtests.tsx</li>
              <li>Remplacer le tableau legacy dans Backtests</li>
              <li>Nettoyer le CSS inutilisé dans Stocks.tsx</li>
            </ul>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default UIValidationDashboard;