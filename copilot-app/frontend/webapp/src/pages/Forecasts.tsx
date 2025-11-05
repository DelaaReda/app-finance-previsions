// Forecasts page - Professional MUI with enhanced filters and visual indicators
// FC-UI-FORECASTS-001: Complete MUI redesign with interactive filters

import { useEffect, useState, useMemo } from 'react';
import type { GridValueFormatterParams, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Container,
  Box,
  Typography,
  Stack,
  Card,
  CardContent,
  Chip,
  Button,
  Alert,
  Skeleton,
  Divider,
  Paper,
  Slider
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  FilterList,
  Refresh,
  Assessment,
  DateRange
} from '@mui/icons-material';
import { apiGet } from '../api/client';
import FreshnessBadge from '../components/ui/FreshnessBadge';
import EmptyState from '../components/ui/EmptyState';
import { safeArray } from '@/lib/safe';
import DataTable from '../components/DataTable';

type Row = {
  id?: string;
  asset_type?: string;
  ticker?: string;
  commodity_name?: string;
  category?: string;
  horizon?: string;
  final_score?: number;
  direction?: string;
  confidence?: number;
  expected_return?: number;
}

type ApiForecastsPayload = {
  rows: Row[];
  count?: number;
  asset_type?: string;
  freshness?: string;
  last_update?: string;
}

async function fetchForecastsFromApi(): Promise<ApiForecastsPayload> {
  const res = await apiGet<ApiForecastsPayload>(`/forecasts`, { asset_type: 'all', horizon: 'all', sort_by: 'score' });
  const data = (res as any).data as ApiForecastsPayload | undefined;
  if (res.ok && data) {
    const safeRows = Array.isArray(data.rows) ? data.rows : [];
    return { ...data, rows: safeRows };
  }
  return { rows: [] } as ApiForecastsPayload;
}

// Helper for score color
function getScoreColor(score: number | null | undefined): string {
  if (score == null) return 'text.secondary';
  if (score >= 7) return 'success.main';
  if (score >= 5) return 'warning.main';
  return 'error.main';
}

// Helper for confidence color
function getConfidenceColor(conf: number | null | undefined): string {
  if (conf == null) return 'text.secondary';
  if (conf >= 0.7) return 'success.main';
  if (conf >= 0.5) return 'warning.main';
  return 'error.main';
}

export default function Forecasts() {
  const [rawData, setRawData] = useState<ApiForecastsPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Filters
  const [horizons, setHorizons] = useState<string[]>([]);
  const [assetTypes, setAssetTypes] = useState<string[]>([]);
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [minScore, setMinScore] = useState<number>(0);

  const horizonOptions = ['short', 'medium', 'long'];
  const assetTypeOptions = ['Commodity', 'Crypto', 'Equity', 'Index', 'FX'];

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const payload = await fetchForecastsFromApi();
      setRawData(payload);
    } catch (e: any) {
      setErr(e?.message || 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const freshness = rawData?.freshness ?? rawData?.last_update ?? null;

  // Filtered rows
  const filteredRows = useMemo(() => {
    const arr = safeArray(rawData?.rows ?? []);
    let filtered = arr;

    if (horizons.length > 0) {
      filtered = filtered.filter(r => r.horizon && horizons.includes(r.horizon));
    }
    if (assetTypes.length > 0) {
      filtered = filtered.filter(r => r.asset_type && assetTypes.includes(r.asset_type));
    }
    if (minConfidence > 0) {
      filtered = filtered.filter(r => r.confidence != null && r.confidence >= minConfidence / 100);
    }
    if (minScore > 0) {
      filtered = filtered.filter(r => r.final_score != null && r.final_score >= minScore);
    }

    return filtered.map((r, i) => ({
      id: r.id ?? `${r.ticker ?? r.commodity_name ?? 'r'}-${r.horizon ?? 'h'}-${i}`,
      ...r
    }));
  }, [rawData, horizons, assetTypes, minConfidence, minScore]);

  const hasActiveFilters = horizons.length > 0 || assetTypes.length > 0 || minConfidence > 0 || minScore > 0;
  const totalCount = safeArray(rawData?.rows ?? []).length;

  const columns: GridColDef[] = useMemo(() => ([
    {
      field: 'asset_type',
      headerName: 'Type',
      width: 120,
      renderCell: (params: GridRenderCellParams) => (
        <Chip label={params.value || '-'} size="small" variant="outlined" />
      )
    },
    { field: 'ticker', headerName: 'Symbole', width: 140, fontWeight: 600 },
    { field: 'commodity_name', headerName: 'Nom', width: 180 },
    {
      field: 'horizon',
      headerName: 'Horizon',
      width: 110,
      renderCell: (params: GridRenderCellParams) => (
        <Chip
          label={params.value || '-'}
          size="small"
          color={params.value === 'long' ? 'info' : params.value === 'medium' ? 'warning' : 'default'}
        />
      )
    },
    {
      field: 'final_score',
      headerName: 'Score',
      width: 100,
      type: 'number',
      valueFormatter: (params: GridValueFormatterParams) => params.value != null ? (params.value as number).toFixed(2) : '-',
      renderCell: (params: GridRenderCellParams) => (
        <Box component="span" sx={{ color: getScoreColor(params.value as number), fontWeight: 600 }}>
          {params.value != null ? (params.value as number).toFixed(2) : '-'}
        </Box>
      )
    },
    {
      field: 'direction',
      headerName: 'Direction',
      width: 120,
      renderCell: (params: GridRenderCellParams) => {
        const dir = params.value as string;
        if (!dir) return <Typography variant="body2">-</Typography>;
        const isUp = dir.toLowerCase() === 'up' || dir === '↑';
        return (
          <Box display="flex" alignItems="center" gap={0.5}>
            {isUp ? (
              <TrendingUp fontSize="small" sx={{ color: 'success.main' }} />
            ) : (
              <TrendingDown fontSize="small" sx={{ color: 'error.main' }} />
            )}
            <Typography variant="body2" sx={{ color: isUp ? 'success.main' : 'error.main', fontWeight: 600 }}>
              {isUp ? 'UP' : 'DOWN'}
            </Typography>
          </Box>
        );
      }
    },
    {
      field: 'confidence',
      headerName: 'Confiance',
      width: 110,
      type: 'number',
      valueFormatter: (p: GridValueFormatterParams) => p.value != null ? `${(p.value as number * 100).toFixed(0)}%` : '-',
      renderCell: (params: GridRenderCellParams) => (
        <Box component="span" sx={{ color: getConfidenceColor(params.value as number), fontWeight: 600 }}>
          {params.value != null ? `${(params.value as number * 100).toFixed(0)}%` : '-'}
        </Box>
      )
    },
    {
      field: 'expected_return',
      headerName: 'Retour attendu',
      width: 140,
      type: 'number',
      valueFormatter: (p: GridValueFormatterParams) => p.value != null ? `${(p.value as number * 100).toFixed(2)}%` : '-',
      renderCell: (params: GridRenderCellParams) => {
        const val = params.value as number;
        if (val == null) return <Typography variant="body2">-</Typography>;
        const formatted = `${(val * 100).toFixed(2)}%`;
        return (
          <Box component="span" sx={{ color: val > 0 ? 'success.main' : 'error.main', fontWeight: 600 }}>
            {formatted}
          </Box>
        );
      }
    },
  ]), []);

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box>
          <Typography variant="h4" component="h1" gutterBottom fontWeight={700}>
            Prévisions de marché
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Analyse quantitative des opportunités d'investissement
          </Typography>
        </Box>

        {/* Stats Cards */}
        <Box display="flex" gap={2} flexWrap="wrap">
          <Card elevation={2} sx={{ flex: '1 1 200px' }}>
            <CardContent>
              <Stack spacing={1}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Assessment color="primary" fontSize="small" />
                  <Typography variant="body2" color="text.secondary">
                    Total prévisions
                  </Typography>
                </Box>
                {loading ? (
                  <Skeleton width="60%" height={32} />
                ) : (
                  <Typography variant="h5" fontWeight={700} color="primary.main">
                    {totalCount}
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>

          <Card elevation={2} sx={{ flex: '1 1 200px' }}>
            <CardContent>
              <Stack spacing={1}>
                <Box display="flex" alignItems="center" gap={1}>
                  <FilterList color="secondary" fontSize="small" />
                  <Typography variant="body2" color="text.secondary">
                    Filtrées
                  </Typography>
                </Box>
                {loading ? (
                  <Skeleton width="60%" height={32} />
                ) : (
                  <Typography variant="h5" fontWeight={700} color="secondary.main">
                    {filteredRows.length}
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>

          <Card elevation={2} sx={{ flex: '1 1 300px' }}>
            <CardContent>
              <Stack spacing={1}>
                <Box display="flex" alignItems="center" gap={1}>
                  <DateRange color="info" fontSize="small" />
                  <Typography variant="body2" color="text.secondary">
                    Dernière mise à jour
                  </Typography>
                </Box>
                {loading ? (
                  <Skeleton width="80%" height={32} />
                ) : (
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="body1" fontWeight={600}>
                      {freshness ? new Date(freshness).toLocaleString('fr-FR') : '—'}
                    </Typography>
                    <FreshnessBadge
                      freshness={freshness ?? undefined}
                      stale={freshness ? (Date.now() - new Date(freshness).getTime() > 3600000) : false}
                    />
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>

          <Box display="flex" alignItems="center">
            <Button
              variant="contained"
              startIcon={<Refresh />}
              onClick={load}
              disabled={loading}
              sx={{ height: 'fit-content' }}
            >
              Rafraîchir
            </Button>
          </Box>
        </Box>

        {/* Filters Card */}
        <Card elevation={2}>
          <CardContent>
            <Stack spacing={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <FilterList color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Filtres
                </Typography>
              </Box>

              <Divider />

              {/* Horizons */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Horizons temporels
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {horizonOptions.map((horizon) => (
                    <Chip
                      key={horizon}
                      label={horizon}
                      onClick={() => {
                        setHorizons(prev =>
                          prev.includes(horizon)
                            ? prev.filter(h => h !== horizon)
                            : [...prev, horizon]
                        );
                      }}
                      color={horizons.includes(horizon) ? "primary" : "default"}
                      variant={horizons.includes(horizon) ? "filled" : "outlined"}
                    />
                  ))}
                </Box>
              </Box>

              {/* Asset Types */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Types d'actifs
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1}>
                  {assetTypeOptions.map((type) => (
                    <Chip
                      key={type}
                      label={type}
                      onClick={() => {
                        setAssetTypes(prev =>
                          prev.includes(type)
                            ? prev.filter(t => t !== type)
                            : [...prev, type]
                        );
                      }}
                      color={assetTypes.includes(type) ? "secondary" : "default"}
                      variant={assetTypes.includes(type) ? "filled" : "outlined"}
                    />
                  ))}
                </Box>
              </Box>

              {/* Min Confidence Slider */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Confiance minimale: {minConfidence}%
                </Typography>
                <Slider
                  value={minConfidence}
                  onChange={(_, value) => setMinConfidence(value as number)}
                  min={0}
                  max={100}
                  step={5}
                  marks={[
                    { value: 0, label: '0%' },
                    { value: 50, label: '50%' },
                    { value: 70, label: '70%' },
                    { value: 100, label: '100%' }
                  ]}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(v) => `${v}%`}
                />
              </Box>

              {/* Min Score Slider */}
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Score minimal: {minScore}
                </Typography>
                <Slider
                  value={minScore}
                  onChange={(_, value) => setMinScore(value as number)}
                  min={0}
                  max={10}
                  step={0.5}
                  marks={[
                    { value: 0, label: '0' },
                    { value: 5, label: '5' },
                    { value: 7, label: '7' },
                    { value: 10, label: '10' }
                  ]}
                  valueLabelDisplay="auto"
                />
              </Box>

              {/* Active Filters Display */}
              {hasActiveFilters && (
                <Alert severity="info" icon={<FilterList />}>
                  <Typography variant="body2" fontWeight={600}>
                    Filtres actifs: {' '}
                    {[
                      horizons.length > 0 && `${horizons.length} horizon(s)`,
                      assetTypes.length > 0 && `${assetTypes.length} type(s)`,
                      minConfidence > 0 && `confiance ≥ ${minConfidence}%`,
                      minScore > 0 && `score ≥ ${minScore}`
                    ].filter(Boolean).join(' • ')}
                  </Typography>
                </Alert>
              )}
            </Stack>
          </CardContent>
        </Card>

        {/* Error Display */}
        {err && (
          <Alert severity="error">
            Erreur lors du chargement: {err}
          </Alert>
        )}

        {/* Loading State */}
        {loading && (
          <Stack spacing={2}>
            <Skeleton variant="rectangular" height={400} />
          </Stack>
        )}

        {/* Empty State */}
        {!loading && !err && filteredRows.length === 0 && (
          <EmptyState
            title="Aucune prévision disponible"
            hint={freshness ? `Dernière mise à jour: ${new Date(freshness).toLocaleString('fr-FR')}` : 'Le modèle calcule en arrière-plan…'}
          />
        )}

        {/* Data Table */}
        {!loading && !err && filteredRows.length > 0 && (
          <DataTable
            title={`Tableau des Prévisions (${filteredRows.length} résultats)`}
            columns={columns}
            rows={filteredRows}
            loading={loading}
            error={null}
            toolbar={true}
            defaultPageSize={25}
            pageSizeOptions={[10, 25, 50, 100]}
            height={600}
          />
        )}
      </Stack>
    </Container>
  );
}
