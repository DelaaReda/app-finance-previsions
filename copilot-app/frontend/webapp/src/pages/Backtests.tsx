// Backtests page - Professional MUI with enhanced metrics visualization
// FC-UI-BACKTESTS-001: Complete MUI redesign with visual stats

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Container,
  Box,
  Typography,
  Stack,
  Card,
  CardContent,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert,
  Skeleton,
  Divider,
  Chip
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  Assessment,
  DateRange,
  ShowChart,
  Warning,
  Timeline
} from '@mui/icons-material'
import { apiGet } from '@/api/client'
import FreshnessBadge from '@/components/ui/FreshnessBadge'
import DataTable from '@/components/DataTable'
import { GridColDef } from '@mui/x-data-grid';

interface BacktestResult {
  results: {
    ok: boolean
    count_days: number
    avg_basket_return: number
    median: number
    stdev: number
    error?: string
  }
  params: {
    horizon: string
    top_n: number
    days_back: number
  }
  generated_at: string
  warning?: string
  detailed_results?: any[] // Added to represent possible detailed backtest results
}

// Helper for return color
function getReturnColor(value: number | null | undefined): string {
  if (value == null) return 'text.secondary';
  if (value > 0) return 'success.main';
  if (value < 0) return 'error.main';
  return 'text.secondary';
}

export default function Backtests() {
  const [horizon, setHorizon] = useState<'1w' | '1m' | '1y'>('1m')
  const [topN, setTopN] = useState(5)
  const [daysBack, setDaysBack] = useState(180)

  const { data, isLoading, error } = useQuery({
    queryKey: ['backtests', horizon, topN, daysBack],
    queryFn: () =>
      apiGet<BacktestResult>('/backtests', {
        horizon,
        'top_n': String(topN),
        'days_back': String(daysBack)
      }).then(r => r.ok ? r.data : Promise.reject(r.error)),
    staleTime: 300000, // 5 minutes
  })

  // Define columns for the detailed results table (if available)
  const backtestColumns: GridColDef[] = [
    {
      field: 'period',
      headerName: 'Période',
      width: 150,
      type: 'string',
    },
    {
      field: 'return',
      headerName: 'Retour',
      width: 120,
      type: 'number',
      valueFormatter: (params) => params.value ? `${(params.value * 100).toFixed(2)}%` : '-',
    },
    {
      field: 'sharpe',
      headerName: 'Sharpe',
      width: 100,
      type: 'number',
      valueFormatter: (params) => params.value ? (params.value).toFixed(3) : '-',
    },
    {
      field: 'max_dd',
      headerName: 'Max DD',
      width: 120,
      type: 'string',
      valueFormatter: (params) => params.value ? (params.value).toFixed(2) : '-',
    },
  ];

  const avgReturn = data?.results?.avg_basket_return;
  const isPositiveReturn = avgReturn != null && avgReturn > 0;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
          <Box>
            <Typography variant="h4" component="h1" gutterBottom fontWeight={700}>
              Backtests - Analyse de Performance
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Évaluation historique de la stratégie de trading
            </Typography>
          </Box>
          {data?.generated_at && (
            <FreshnessBadge
              freshness={data.generated_at}
              stale={new Date().getTime() - new Date(data.generated_at).getTime() > 3600000}
            />
          )}
        </Box>

        {/* Configuration Card */}
        <Card elevation={2}>
          <CardContent>
            <Stack spacing={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <ShowChart color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Configuration du Backtest
                </Typography>
              </Box>

              <Divider />

              <Grid container spacing={3}>
                <Grid item xs={12} sm={4}>
                  <FormControl fullWidth>
                    <InputLabel>Horizon</InputLabel>
                    <Select
                      value={horizon}
                      label="Horizon"
                      onChange={(e) => setHorizon(e.target.value as '1w' | '1m' | '1y')}
                    >
                      <MenuItem value="1w">1 Semaine</MenuItem>
                      <MenuItem value="1m">1 Mois</MenuItem>
                      <MenuItem value="1y">1 An</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Top-N actifs"
                    value={topN}
                    onChange={(e) => setTopN(Math.max(1, Math.min(20, parseInt(e.target.value) || 5)))}
                    inputProps={{ min: 1, max: 20 }}
                    helperText="Nombre d'actifs dans le panier"
                  />
                </Grid>

                <Grid item xs={12} sm={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Jours historiques"
                    value={daysBack}
                    onChange={(e) => setDaysBack(Math.max(30, Math.min(365, parseInt(e.target.value) || 180)))}
                    inputProps={{ min: 30, max: 365 }}
                    helperText="Période d'analyse"
                  />
                </Grid>
              </Grid>

              <Box>
                <Alert severity="info" icon={<Timeline />}>
                  <Typography variant="body2">
                    Configuration: Horizon <strong>{horizon}</strong>, Top-<strong>{topN}</strong> actifs, <strong>{daysBack}</strong> jours d'historique
                  </Typography>
                </Alert>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        {/* Loading State */}
        {isLoading && (
          <Stack spacing={2}>
            <Skeleton variant="rectangular" height={200} />
            <Skeleton variant="rectangular" height={300} />
          </Stack>
        )}

        {/* Error State */}
        {error && (
          <Alert severity="error">
            Erreur lors du chargement: {String(error)}
          </Alert>
        )}

        {/* Results */}
        {data && data.results && (
          <>
            {/* Metrics Grid */}
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={2}>
                  <CardContent>
                    <Stack spacing={1}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <DateRange color="primary" fontSize="small" />
                        <Typography variant="body2" color="text.secondary">
                          Jours de données
                        </Typography>
                      </Box>
                      <Typography variant="h4" fontWeight={700} color="primary.main">
                        {data.results.count_days ?? 0}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={2}>
                  <CardContent>
                    <Stack spacing={1}>
                      <Box display="flex" alignItems="center" gap={1}>
                        {isPositiveReturn ? (
                          <TrendingUp color="success" fontSize="small" />
                        ) : (
                          <TrendingDown color="error" fontSize="small" />
                        )}
                        <Typography variant="body2" color="text.secondary">
                          Retour moyen
                        </Typography>
                      </Box>
                      <Typography
                        variant="h4"
                        fontWeight={700}
                        sx={{ color: getReturnColor(avgReturn) }}
                      >
                        {avgReturn != null ? `${(avgReturn * 100).toFixed(2)}%` : 'N/A'}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={2}>
                  <CardContent>
                    <Stack spacing={1}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Assessment color="warning" fontSize="small" />
                        <Typography variant="body2" color="text.secondary">
                          Écart-type
                        </Typography>
                      </Box>
                      <Typography variant="h4" fontWeight={700} color="warning.main">
                        {data.results.stdev != null ? `${(data.results.stdev * 100).toFixed(2)}%` : 'N/A'}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={2}>
                  <CardContent>
                    <Stack spacing={1}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <ShowChart color="info" fontSize="small" />
                        <Typography variant="body2" color="text.secondary">
                          Médiane
                        </Typography>
                      </Box>
                      <Typography variant="h4" fontWeight={700} color="info.main">
                        {data.results.median != null ? `${(data.results.median * 100).toFixed(2)}%` : 'N/A'}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Details Card */}
            <Card elevation={2}>
              <CardContent>
                <Stack spacing={2}>
                  <Typography variant="h6" fontWeight={600}>
                    Paramètres de l'analyse
                  </Typography>

                  <Divider />

                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6} md={3}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Horizon
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          {data.params?.horizon || 'N/A'}
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Panier Top-N
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          Top-{data.params?.top_n || 'N/A'}
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Période historique
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          {data.params?.days_back || 'N/A'} jours
                        </Typography>
                      </Box>
                    </Grid>

                    <Grid item xs={12} sm={6} md={3}>
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Généré le
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          {data.generated_at ? new Date(data.generated_at).toLocaleString('fr-FR') : 'N/A'}
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  {data.warning && (
                    <>
                      <Divider />
                      <Alert severity="warning" icon={<Warning />}>
                        <Typography variant="body2">
                          <strong>Avertissement:</strong> {data.warning}
                        </Typography>
                      </Alert>
                    </>
                  )}
                </Stack>
              </CardContent>
            </Card>

            {/* Detailed Results Table */}
            {data.detailed_results && data.detailed_results.length > 0 && (
              <DataTable
                title="Résultats détaillés des backtests"
                columns={backtestColumns}
                rows={data.detailed_results}
                toolbar={true}
                defaultPageSize={10}
                pageSizeOptions={[5, 10, 25]}
                height={400}
              />
            )}
          </>
        )}
      </Stack>
    </Container>
  )
}