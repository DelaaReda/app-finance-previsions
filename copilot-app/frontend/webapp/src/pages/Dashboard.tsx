// Dashboard principal - Vue d'ensemble avec Top 3 Signaux/Risques
// FC-UI-DASHBOARD-001: Complete MUI redesign for production delivery

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/services/api'
import {
  Container,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Stack,
  Alert,
  Skeleton,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  Paper
} from '@mui/material'
import {
  TrendingUp,
  TrendingDown,
  Assessment,
  DateRange,
  ShowChart,
  FilterList
} from '@mui/icons-material'
import TopSignals from '@/components/signals/TopSignals'
import TopRisks from '@/components/signals/TopRisks'
import { safeArray, hasItems } from '@/lib/safe'
import type { CompositeSignal } from '@/types/common.types'

type DashboardData = {
  last_forecast_dt?: string | null
  forecasts_count?: number
  tickers?: number
  horizons?: string[]
  last_macro_dt?: string | null
  last_quality_dt?: string | null
  filtered_signals?: CompositeSignal[]
  filtered_risks?: CompositeSignal[]
  filtered_ticker_count?: number
  generated_at?: string
  filter_applied?: {
    sectors: string[]
    horizons: string[]
    themes: string[]
    tickers: string[]
  }
  error?: string
}

export default function Dashboard() {
  const [sectors, setSectors] = useState<string[]>([])
  const [horizons, setHorizons] = useState<string[]>([])
  const [themes, setThemes] = useState<string[]>([])
  const [tickersInput, setTickersInput] = useState('')
  const [includeSignals, setIncludeSignals] = useState<boolean>(false)

  // Options
  const sectorOptions = ["Technology", "Healthcare", "Financials", "Consumer", "Industrials", "Energy", "Utilities", "Real Estate"]
  const horizonOptions = ["short", "medium", "long"]
  const themeOptions = ["growth", "value", "momentum", "dividend", "quality"]

  const { data, isLoading, error, isFetching } = useQuery<DashboardData>({
    queryKey: ['dashboard', { sectors, horizons, themes, tickers: tickersInput, includeSignals }],
    queryFn: async () => {
      const params: Record<string, string> = {}
      if (sectors.length > 0) params.sectors = sectors.join(',')
      if (horizons.length > 0) params.horizons = horizons.join(',')
      if (themes.length > 0) params.themes = themes.join(',')
      if (tickersInput.trim()) params.tickers = tickersInput.trim()
      if (includeSignals) params.include_signals = '1'

      const response = await apiGet<DashboardData>('/dashboard/kpis', params)
      if (!response.ok) {
        throw new Error(response.error || 'Échec du chargement du dashboard')
      }
      return response.data
    },
    staleTime: 15_000,
  })

  const signals = safeArray(data?.filtered_signals)
  const risks = safeArray(data?.filtered_risks)
  const generatedAt = data?.generated_at ? new Date(data.generated_at) : undefined
  const hasActiveFilters = sectors.length > 0 || horizons.length > 0 || themes.length > 0 || tickersInput.trim() || includeSignals

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box>
          <Typography variant="h4" component="h1" gutterBottom fontWeight={700}>
            Dashboard - Vue d'ensemble
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Analyse complète des prévisions, signaux et risques de marché
          </Typography>
        </Box>

        {/* Filters Card */}
        <Card elevation={2}>
          <CardContent>
            <Stack spacing={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <FilterList color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Filtres d'analyse
                </Typography>
              </Box>

              <Divider />

              {/* Sectors */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Secteurs
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {sectorOptions.map((sector) => (
                    <Chip
                      key={sector}
                      label={sector}
                      onClick={() => {
                        setSectors(prev =>
                          prev.includes(sector)
                            ? prev.filter(s => s !== sector)
                            : [...prev, sector]
                        )
                      }}
                      color={sectors.includes(sector) ? "primary" : "default"}
                      variant={sectors.includes(sector) ? "filled" : "outlined"}
                    />
                  ))}
                </Box>
              </Box>

              {/* Horizons */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Horizons temporels
                </Typography>
                <ToggleButtonGroup
                  value={horizons}
                  onChange={(_, newHorizons) => setHorizons(newHorizons)}
                  aria-label="horizons"
                  size="small"
                >
                  {horizonOptions.map((horizon) => (
                    <ToggleButton key={horizon} value={horizon} aria-label={horizon}>
                      {horizon}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              </Box>

              {/* Themes */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Thèmes d'investissement
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {themeOptions.map((theme) => (
                    <Chip
                      key={theme}
                      label={theme}
                      onClick={() => {
                        setThemes(prev =>
                          prev.includes(theme)
                            ? prev.filter(t => t !== theme)
                            : [...prev, theme]
                        )
                      }}
                      color={themes.includes(theme) ? "secondary" : "default"}
                      variant={themes.includes(theme) ? "filled" : "outlined"}
                    />
                  ))}
                </Box>
              </Box>

              {/* Tickers Input */}
              <TextField
                label="Tickers spécifiques"
                placeholder="ex: AAPL, MSFT, GOOGL"
                value={tickersInput}
                onChange={(e) => setTickersInput(e.target.value)}
                size="small"
                fullWidth
                helperText="Séparez les tickers par des virgules"
              />

              {/* Include Signals Toggle */}
              <Box>
                <Chip
                  label={includeSignals ? "Mode détaillé: ACTIVÉ" : "Mode détaillé: DÉSACTIVÉ"}
                  onClick={() => setIncludeSignals(!includeSignals)}
                  color={includeSignals ? "success" : "default"}
                  variant={includeSignals ? "filled" : "outlined"}
                  disabled={isFetching}
                  icon={includeSignals ? <ShowChart /> : undefined}
                />
                <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1 }}>
                  Le mode détaillé calcule les signaux et risques (plus lent mais plus complet)
                </Typography>
              </Box>

              {/* Active Filters Display */}
              {hasActiveFilters && (
                <Alert severity="info" icon={<FilterList />}>
                  <Typography variant="body2" fontWeight={600}>
                    Filtres actifs: {' '}
                    {[
                      sectors.length > 0 && `${sectors.length} secteur(s)`,
                      horizons.length > 0 && `${horizons.length} horizon(s)`,
                      themes.length > 0 && `${themes.length} thème(s)`,
                      tickersInput.trim() && 'tickers spécifiques',
                      includeSignals && 'mode détaillé'
                    ].filter(Boolean).join(' • ')}
                  </Typography>
                </Alert>
              )}
            </Stack>
          </CardContent>
        </Card>

        {/* KPIs Grid */}
        <Grid container spacing={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={2}>
              <CardContent>
                <Stack spacing={1}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <DateRange color="primary" />
                    <Typography variant="body2" color="text.secondary">
                      Dernière prévision
                    </Typography>
                  </Box>
                  {isLoading ? (
                    <Skeleton variant="text" width="80%" height={40} />
                  ) : (
                    <Typography variant="h5" fontWeight={700}>
                      {data?.last_forecast_dt || '—'}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={2}>
              <CardContent>
                <Stack spacing={1}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Assessment color="secondary" />
                    <Typography variant="body2" color="text.secondary">
                      Nombre de prévisions
                    </Typography>
                  </Box>
                  {isLoading ? (
                    <Skeleton variant="text" width="60%" height={40} />
                  ) : (
                    <Typography variant="h5" fontWeight={700} color="secondary.main">
                      {data?.forecasts_count ?? 0}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={2}>
              <CardContent>
                <Stack spacing={1}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <TrendingUp color="success" />
                    <Typography variant="body2" color="text.secondary">
                      Tickers suivis
                    </Typography>
                  </Box>
                  {isLoading ? (
                    <Skeleton variant="text" width="50%" height={40} />
                  ) : (
                    <Typography variant="h5" fontWeight={700} color="success.main">
                      {data?.tickers ?? 0}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card elevation={2}>
              <CardContent>
                <Stack spacing={1}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <ShowChart color="info" />
                    <Typography variant="body2" color="text.secondary">
                      Horizons
                    </Typography>
                  </Box>
                  {isLoading ? (
                    <Skeleton variant="text" width="70%" height={40} />
                  ) : (
                    <Typography variant="h6" fontWeight={600} color="info.main">
                      {(data?.horizons || []).join(', ') || '—'}
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Error Display */}
        {error && (
          <Alert severity="error">
            Erreur lors du chargement: {String(error)}
          </Alert>
        )}
        {!error && data?.error && (
          <Alert severity="warning">
            {data.error}
          </Alert>
        )}

        {/* Meta Information */}
        {!isLoading && !error && (
          <Paper elevation={1} sx={{ p: 2, bgcolor: 'background.default' }}>
            <Stack spacing={1}>
              <Typography variant="body2" color="text.secondary">
                <strong>Univers analysé:</strong> {data?.filtered_ticker_count ?? data?.tickers ?? 0} tickers
              </Typography>
              {generatedAt && (
                <Typography variant="body2" color="text.secondary">
                  <strong>Dernière mise à jour:</strong> {generatedAt.toLocaleString('fr-FR')}
                </Typography>
              )}
            </Stack>
          </Paper>
        )}

        {/* Loading State */}
        {(isLoading || isFetching) && (
          <Stack spacing={2}>
            <Skeleton variant="rectangular" height={200} />
            <Skeleton variant="rectangular" height={200} />
          </Stack>
        )}

        {/* Signals and Risks */}
        {!isLoading && !error && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TopSignals
                signals={signals}
                title="Top 3 Signaux"
                emptyMessage="Aucun signal détecté pour les filtres sélectionnés."
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TopRisks
                risks={risks}
                title="Top 3 Risques"
                emptyMessage="Aucun risque majeur détecté pour les filtres sélectionnés."
              />
            </Grid>
          </Grid>
        )}
      </Stack>
    </Container>
  )
}
